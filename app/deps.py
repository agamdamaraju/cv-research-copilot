import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR.parent / "data"
PDF_DIR = DATA_DIR / "pdfs"
STORE_DIR = DATA_DIR / "store"
INDEX_DIR = DATA_DIR / "index"

for d in [PDF_DIR, STORE_DIR, INDEX_DIR]:
    d.mkdir(parents=True, exist_ok=True)

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
MODEL_PRIMARY = os.getenv("MODEL_PRIMARY", "openai/gpt-4o-mini")
MODEL_LOCAL = os.getenv("MODEL_LOCAL", "ollama/llama3.1:8b-instruct")
EMBED_MODEL = os.getenv("EMBED_MODEL", "BAAI/bge-m3")
RERANK_MODEL = os.getenv("RERANK_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
TOP_K = int(os.getenv("TOP_K", "8"))
USE_LOCAL = os.getenv("USE_LOCAL", "0") == "1"