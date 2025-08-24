from fastapi import APIRouter, HTTPException
import json, re
from app.schemas import ExtractRequest, ExtractResponse, PaperJSON
from app.deps import INDEX_DIR, EMBED_MODEL, RERANK_MODEL, MODEL_PRIMARY, MODEL_LOCAL, USE_LOCAL, OPENAI_API_KEY, TOP_K
from app.core.embed import IndexStore
from app.core.retrieve import Retriever
from app.core.prompts import JSON_SYSTEM, JSON_USER_TEMPLATE, JSON_SCHEMA_STR
from app.core.llm import LLMClient
import requests
import math

def _coerce_str(x) -> str:
    if x is None:
        return ""
    if isinstance(x, str):
        return x.strip()
    if isinstance(x, dict):
        # common LLM patterns
        if "title" in x and isinstance(x["title"], str):
            return x["title"].strip()
        if "text" in x and isinstance(x["text"], str):
            return x["text"].strip()
    if isinstance(x, list):
        parts = []
        for el in x:
            if isinstance(el, str):
                parts.append(el.strip())
            elif isinstance(el, dict):
                if "title" in el and isinstance(el["title"], str):
                    parts.append(el["title"].strip())
                elif "text" in el and isinstance(el["text"], str):
                    parts.append(el["text"].strip())
                else:
                    parts.append(str(el))
            else:
                parts.append(str(el))
        return " ".join(p for p in parts if p)
    return str(x).strip()


def _coerce_float(x):
    # accepts "28.7", "28.7%", "1,234.5", or numbers
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        s = x.strip().replace(",", "")
        s = s[:-1] if s.endswith("%") else s
        try:
            return float(s)
        except Exception:
            return None
    return None


def _coerce_int(x):
    if isinstance(x, int):
        return x
    if isinstance(x, float) and x.is_integer():
        return int(x)
    if isinstance(x, str) and x.strip().isdigit():
        return int(x.strip())
    return None


def normalize_paperjson(raw: dict) -> dict:
    """
    Tolerant normalizer: fixes common LLM schema drift so Pydantic can validate.
    """
    out = {}
    # title
    out["title"] = _coerce_str(raw.get("title"))

    # tasks
    tasks = raw.get("tasks") or []
    out["tasks"] = []
    if isinstance(tasks, list):
        for t in tasks:
            out["tasks"].append(_coerce_str(t))
    elif isinstance(tasks, str):
        out["tasks"] = [s.strip() for s in tasks.split(",") if s.strip()]
    else:
        out["tasks"] = []

    # methods
    out["methods"] = []
    for m in raw.get("methods") or []:
        if not isinstance(m, dict):
            continue
        name = _coerce_str(m.get("name"))
        components = m.get("components") or []
        losses = m.get("losses") or []
        if isinstance(components, str):
            components = [c.strip() for c in components.split(",") if c.strip()]
        if isinstance(losses, str):
            losses = [c.strip() for c in losses.split(",") if c.strip()]
        out["methods"].append({
            "name": name,
            "components": [ _coerce_str(c) for c in components if _coerce_str(c) ],
            "losses": [ _coerce_str(c) for c in losses if _coerce_str(c) ],
        })

    # datasets
    out["datasets"] = []
    for d in raw.get("datasets") or []:
        if isinstance(d, dict):
            out["datasets"].append({
                "name": _coerce_str(d.get("name")),
                "split": (_coerce_str(d.get("split")) or None)
            })
        elif isinstance(d, str):
            out["datasets"].append({"name": d.strip(), "split": None})

    # metrics
    out["metrics"] = []
    for m in raw.get("metrics") or []:
        if not isinstance(m, dict):
            continue
        val = _coerce_float(m.get("value"))
        page = _coerce_int(m.get("page")) or 1
        ds = _coerce_str(m.get("dataset"))
        met = _coerce_str(m.get("metric"))
        if val is not None and ds and met:
            out["metrics"].append({
                "dataset": ds,
                "metric": met,
                "value": val,
                "page": page
            })

    # ablations
    out["ablations"] = []
    for a in raw.get("ablations") or []:
        if isinstance(a, dict):
            out["ablations"].append({
                "variable": _coerce_str(a.get("variable")),
                "best_value": a.get("best_value"),
            })
        else:
            out["ablations"].append({"variable": _coerce_str(a), "best_value": None})

    return out

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
    # user = JSON_USER_TEMPLATE.format(context=context) + "\nReturn ONLY a single JSON object, no markdown, no explanation."
    user = (
        JSON_USER_TEMPLATE.format(context=context)
        + "\nReturn ONLY one JSON object. No markdown. "
        + "Keys must be exactly: title (string), tasks (list of strings), methods (list of {name, components, losses}), "
        "datasets (list of {name, split|null}), metrics (list of {dataset, metric, value:number, page:int}), "
        "ablations (list of {variable, best_value}). "
        "Do not wrap strings in nested objects like {'text': ...}."
    )
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
        data = normalize_paperjson(data)
    except Exception:
        # Attach a snippet of the model output to help debugging
        snippet = (raw or "")[:400]
        raise HTTPException(502, f"Model did not return clean JSON. First 400 chars:\n{snippet}")

    pj = PaperJSON.model_validate(data)
    return ExtractResponse(data=pj)