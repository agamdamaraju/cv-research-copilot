import faiss, json
import numpy as np
from pathlib import Path
from sentence_transformers import SentenceTransformer
from typing import List

class IndexStore:
    def __init__(self, model_name: str, index_dir: Path):
        self.model = SentenceTransformer(model_name)
        self.index_dir = index_dir
        self.index_dir.mkdir(parents=True, exist_ok=True)

    def _paths(self, doc_id: str):
        base = self.index_dir / f"{doc_id}"
        return base.with_suffix(".faiss"), base.with_suffix(".meta.json")

    def build(self, doc_id: str, chunks: List[dict]):
        texts = [c["text"] for c in chunks]
        embeds = self.model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)
        d = embeds.shape[1]
        index = faiss.IndexFlatIP(d)
        index.add(embeds)
        idx_path, meta_path = self._paths(doc_id)
        faiss.write_index(index, str(idx_path))
        meta = {"doc_id": doc_id, "n": len(chunks), "chunks": chunks}
        meta_path.write_text(json.dumps(meta, ensure_ascii=False))

    def search(self, doc_id: str, query: str, top_k: int = 50):
        idx_path, meta_path = self._paths(doc_id)
        index = faiss.read_index(str(idx_path))
        meta = json.loads(meta_path.read_text())
        qv = self.model.encode([query], normalize_embeddings=True, convert_to_numpy=True)
        scores, idxs = index.search(qv, top_k)
        results = []
        for rank, (i, s) in enumerate(zip(idxs[0], scores[0])):
            if 0 <= i < meta["n"]:
                ch = meta["chunks"][i]
                results.append({"rank": rank, "score": float(s), **ch})
        return results