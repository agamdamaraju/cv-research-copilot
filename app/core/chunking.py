from __future__ import annotations
from typing import List
from dataclasses import dataclass
import json
from pathlib import Path

@dataclass
class Chunk:
    chunk_id: str
    doc_id: str
    pages: List[int]
    text: str
    block_ids: List[str]


def chunk_blocks(blocks: List[dict], doc_id: str, out_path: Path, max_chars: int = 1800) -> List[Chunk]:
    chunks: List[Chunk] = []
    cur_text, cur_pages, cur_blocks = [], set(), []

    def flush():
        nonlocal chunks, cur_text, cur_pages, cur_blocks
        if not cur_text:
            return
        cid = f"{doc_id}:{len(chunks)}"
        chunk = Chunk(
            chunk_id=cid,
            doc_id=doc_id,
            pages=sorted(list(cur_pages)),
            text="\n".join(cur_text),
            block_ids=cur_blocks,
        )
        chunks.append(chunk)
        cur_text, cur_pages, cur_blocks = [], set(), []

    for b in blocks:
        kind = b.get("kind")
        txt = b.get("text", "").strip()
        if not txt:
            continue
        if kind == "table":
            flush()
            cid = f"{doc_id}:{len(chunks)}"
            chunks.append(
                Chunk(
                    chunk_id=cid,
                    doc_id=doc_id,
                    pages=[b.get("page")],
                    text=txt,
                    block_ids=[b.get("id")],
                )
            )
            continue
        if sum(len(t) for t in cur_text) + len(txt) + 1 > max_chars:
            flush()
        cur_text.append(txt)
        cur_pages.add(b.get("page"))
        cur_blocks.append(b.get("id"))
    flush()

    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        for ch in chunks:
            f.write(
                json.dumps(
                    {
                        "chunk_id": ch.chunk_id,
                        "doc_id": ch.doc_id,
                        "pages": ch.pages,
                        "text": ch.text,
                        "block_ids": ch.block_ids,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
    return chunks