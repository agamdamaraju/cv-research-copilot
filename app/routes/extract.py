from fastapi import APIRouter, HTTPException
import json, re
from app.schemas import ExtractRequest, ExtractResponse, PaperJSON
from app.deps import INDEX_DIR, EMBED_MODEL, RERANK_MODEL, MODEL_PRIMARY, MODEL_LOCAL, USE_LOCAL, OPENAI_API_KEY, TOP_K
from app.core.embed import IndexStore
from app.core.retrieve import Retriever
from app.core.prompts import JSON_SYSTEM, JSON_USER_TEMPLATE, JSON_SCHEMA_STR
from app.core.llm import LLMClient
import requests

router = APIRouter()

def _strip_code_fences(s: str) -> str:
    s = s.strip()
    # remove leading/trailing ```json ... ``` or ``` ... ```
    s = re.sub(r"^\s*```(?:json)?\s*", "", s, flags=re.IGNORECASE)
    s = re.sub(r"\s*```\s*$", "", s)
    return s.strip()

def _extract_first_balanced_json(s: str):
    """
    Find the first balanced {...} object (handles extra commentary before/after).
    """
    start = None
    depth = 0
    for i, ch in enumerate(s):
        if ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start is not None:
                    yield s[start:i+1]

def parse_json_safely(text: str) -> dict:
    """
    Be tolerant of LLM outputs (code fences, extra prose, multiple JSON objects).
    Returns the first JSON object that parses.
    """
    if not text or not text.strip():
        raise ValueError("empty response")

    # 1) fast path: direct
    t = _strip_code_fences(text)
    try:
        return json.loads(t)
    except Exception:
        pass

    # 2) widest braces
    first = t.find("{")
    last = t.rfind("}")
    if first != -1 and last != -1 and last > first:
        candidate = t[first:last+1]
        try:
            return json.loads(candidate)
        except Exception:
            pass

    # 3) scan balanced objects, pick the first that parses
    for obj in _extract_first_balanced_json(t):
        try:
            return json.loads(obj)
        except Exception:
            continue

    # Nothing parsed
    raise ValueError("could not parse JSON from model output")

@router.post("/", response_model=ExtractResponse)
async def extract(req: ExtractRequest):
    index = IndexStore(EMBED_MODEL, INDEX_DIR)
    retriever = Retriever(index, RERANK_MODEL)

    # Broad CV extraction query to pull metrics/tables/method parts
    q = "methods loss function architecture dataset split metric table AP mAP mIoU results ablation sota"
    chunks = retriever.retrieve(req.doc_id, q, k=TOP_K)
    if not chunks:
        raise HTTPException(404, "No content found for extraction. Did you ingest the PDF?")

    context = Retriever.pack_context(chunks)
    system = JSON_SYSTEM.format(schema=JSON_SCHEMA_STR)
    # Stronger instruction to reduce markdown
    user = JSON_USER_TEMPLATE.format(context=context) + "\nReturn ONLY a single JSON object, no markdown, no explanation."

    llm = LLMClient(MODEL_PRIMARY, MODEL_LOCAL, USE_LOCAL, OPENAI_API_KEY)

    try:
        raw = llm.generate(system, user, expect_json=True)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 401:
            raise HTTPException(401, "OpenAI auth failed: set OPENAI_API_KEY in .env, or set USE_LOCAL=1 to use Ollama.")
        raise

    # Robust parsing
    try:
        data = parse_json_safely(raw)
    except Exception:
        # Attach a snippet of the model output to help debugging
        snippet = (raw or "")[:400]
        raise HTTPException(502, f"Model did not return clean JSON. First 400 chars:\n{snippet}")

    pj = PaperJSON.model_validate(data)
    return ExtractResponse(data=pj)