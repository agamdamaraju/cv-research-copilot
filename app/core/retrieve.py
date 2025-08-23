from app.core.embed import IndexStore
from app.deps import TOP_K

try:
    from sentence_transformers import CrossEncoder
    HAVE_XENC = True
except Exception:
    HAVE_XENC = False

class Retriever:
    def __init__(self, index: IndexStore, rerank_model: str | None = None):
        self.index = index
        self.reranker = CrossEncoder(rerank_model) if (HAVE_XENC and rerank_model) else None

    def retrieve(self, doc_id: str, question: str, k: int = TOP_K):
        prelim = self.index.search(doc_id, question, top_k=50)
        if not prelim:
            return []
        if self.reranker:
            pairs = [(question, p["text"]) for p in prelim]
            scores = self.reranker.predict(pairs)
            for p, s in zip(prelim, scores):
                p["rerank"] = float(s)
            prelim.sort(key=lambda x: x.get("rerank", 0), reverse=True)
        else:
            prelim.sort(key=lambda x: x.get("score", 0), reverse=True)
        return prelim[:k]

    @staticmethod
    def pack_context(chunks):
        packed = []
        for ch in chunks:
            pages = ch.get("pages", [])
            tag = f"[DOC:{ch.get('doc_id')} p:{','.join(map(str, pages))}]"
            packed.append(f"{tag}\n{ch.get('text','').strip()}")
        return "\n\n".join(packed)