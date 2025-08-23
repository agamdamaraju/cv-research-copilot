from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import hashlib
import fitz  

from app.schemas import IngestResponse
from app.deps import PDF_DIR, STORE_DIR, INDEX_DIR, EMBED_MODEL
from app.core.parsing import parse_pdf_to_blocks
from app.core.chunking import chunk_blocks
from app.core.embed import IndexStore

router = APIRouter()


def _hash_file(contents: bytes) -> str:
    """Stable doc_id based on file content."""
    h = hashlib.md5()
    h.update(contents)
    return h.hexdigest()


@router.post("/", response_model=IngestResponse)
async def ingest_pdf(file: UploadFile = File(...)):
    """Upload a PDF -> save -> parse -> chunk -> embed -> return doc_id and page count."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="Empty file.")

    # Persist the original PDF
    doc_id = _hash_file(pdf_bytes)
    pdf_path = PDF_DIR / f"{doc_id}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    # Parse to blocks and chunk
    blocks_path = STORE_DIR / f"{doc_id}.blocks.jsonl"
    chunks_path = STORE_DIR / f"{doc_id}.chunks.jsonl"
    blocks = [b.__dict__ for b in parse_pdf_to_blocks(pdf_path, doc_id, blocks_path)]
    chunks = [c.__dict__ for c in chunk_blocks(blocks, doc_id, chunks_path)]

    # Build vector index
    index = IndexStore(EMBED_MODEL, INDEX_DIR)
    index.build(doc_id, chunks)

    # Page count via PyMuPDF
    try:
        with fitz.open(str(pdf_path)) as doc:
            pages = len(doc)
    except Exception:
        pages = 0

    return IngestResponse(doc_id=doc_id, pages=pages)