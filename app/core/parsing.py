from __future__ import annotations
import fitz  # PyMuPDF
import pdfplumber
from dataclasses import dataclass, asdict
from typing import List, Literal, Optional, Tuple
import json, uuid
from pathlib import Path


@dataclass
class Block:
    doc_id: str
    page: int
    kind: Literal["heading", "paragraph", "table", "figure_caption"]
    text: str
    bbox: Optional[Tuple[float, float, float, float]]
    section_path: List[str]
    id: str


def _is_heading(text: str) -> bool:
    """Lightweight heading heuristic: short + numbered/uppercase/title-ish."""
    if not text:
        return False
    s = text.strip()
    if len(s) <= 80 and (s.isupper() or any(s.startswith(f"{i}.") for i in range(1, 10))):
        return True
    # You can extend with more heuristics if needed.
    return False


def parse_pdf_to_blocks(pdf_path: Path, doc_id: str, store_path: Path) -> List[Block]:
    """
    Extract text lines (as headings/paragraphs) via PyMuPDF,
    and tables via pdfplumber. Persist JSONL to `store_path`.
    """
    blocks: List[Block] = []

    # ---- Text & headings via PyMuPDF ----
    with fitz.open(str(pdf_path)) as doc:
        for i, page in enumerate(doc):
            page_num = i + 1
            # 'dict' preserves some layout; we'll stitch spans into lines
            text_dict = page.get_text("dict")
            section_stack: List[str] = []
            for b in text_dict.get("blocks", []):
                for l in b.get("lines", []):
                    line_text = " ".join(
                        (s.get("text", "") or "").strip()
                        for s in l.get("spans", [])
                    ).strip()
                    if not line_text:
                        continue
                    kind = "heading" if _is_heading(line_text) else "paragraph"
                    blk = Block(
                        doc_id=doc_id,
                        page=page_num,
                        kind=kind,
                        text=line_text,
                        bbox=None,                  # Could capture bbox from spans if desired
                        section_path=section_stack.copy(),
                        id=str(uuid.uuid4()),
                    )
                    blocks.append(blk)
                    if kind == "heading":
                        # Maintain a simple section path of the last few headings
                        section_stack.append(line_text)
                        section_stack = section_stack[-3:]

    # ---- Tables via pdfplumber (best effort) ----
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                page_num = i + 1
                try:
                    tables = page.extract_tables() or []
                except Exception:
                    tables = []
                for tbl in tables:
                    # Represent table as TSV lines to preserve some structure
                    rows = ["\t".join("" if c is None else str(c) for c in row) for row in tbl]
                    text = "\n".join(rows)
                    blocks.append(
                        Block(
                            doc_id=doc_id,
                            page=page_num,
                            kind="table",
                            text=text,
                            bbox=None,
                            section_path=[],
                            id=str(uuid.uuid4()),
                        )
                    )
    except Exception:
        # Some PDFs (scanned) may fail; don't block ingestion
        pass

    # ---- Persist for downstream steps ----
    store_path.parent.mkdir(parents=True, exist_ok=True)
    with store_path.open("w", encoding="utf-8") as f:
        for blk in blocks:
            f.write(json.dumps(asdict(blk), ensure_ascii=False) + "\n")

    return blocks