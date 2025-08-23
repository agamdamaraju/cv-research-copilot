from fastapi import APIRouter, HTTPException
from app.schemas import AskRequest, AskResponse
from app.deps import INDEX_DIR, EMBED_MODEL, RERANK_MODEL, MODEL_PRIMARY, MODEL_LOCAL, USE_LOCAL, OPENAI_API_KEY, TOP_K
from app.core.embed import IndexStore
from app.core.retrieve import Retriever
from app.core.prompts import QA_SYSTEM, QA_USER_TEMPLATE
from app.core.llm import LLMClient

router = APIRouter()

@router.post("/", response_model=AskResponse)
async def ask(req: AskRequest):
    index = IndexStore(EMBED_MODEL, INDEX_DIR)
    retriever = Retriever(index, RERANK_MODEL)
    chunks = retriever.retrieve(req.doc_id, req.question, k=TOP_K)
    if not chunks:
        raise HTTPException(404, "No relevant chunks found. Did you ingest the PDF?")
    context = Retriever.pack_context(chunks)

    user_prompt = QA_USER_TEMPLATE.format(question=req.question, context=context)
    llm = LLMClient(MODEL_PRIMARY, MODEL_LOCAL, USE_LOCAL, OPENAI_API_KEY)
    answer = llm.generate(QA_SYSTEM, user_prompt, expect_json=False)

    return AskResponse(answer=answer)