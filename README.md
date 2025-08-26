# CV Research Copilot (LLM)

A domain-specific RAG assistant for **computer vision papers**.  
Upload a PDF: ask questions with **page-level citations** like `[p:12]`: extract a **strict JSON** of methods/datasets/metrics/ablations (with page refs for every number).  
Runs great on a MacBook Pro (M4 series). Supports **OpenAI** or local **Ollama**; ships with **Docker**.

---

## Demo
https://github.com/user-attachments/assets/213a355b-df75-4046-a6af-0649c166bc65

Paper used in this demo:
Lin, T., Dollár, P., Girshick, R.B., He, K., Hariharan, B., & Belongie, S.J. (2016). Feature Pyramid Networks for Object Detection. 2017 IEEE Conference on Computer Vision and Pattern Recognition (CVPR), 936-944.




---

## Features

- **Paper Q&A** with **inline page citations** (`[p:##]`)
- **Structured JSON extraction** of `title`, `tasks`, `methods`, `datasets`, `metrics`, `ablations`
- **Retriever-Reranker**: FAISS → CrossEncoder rerank → LLM
- **Parsing stack**: PyMuPDF + pdfplumber (tables)
- **LLM routing**: OpenAI (gpt-4o-mini) or Ollama (Llama 3.1) via a single client
- **Streamlit UI** + **FastAPI** backend
- **Dockerized** with profiles for local (Ollama) or OpenAI mode

---

## Project Structure

```text
cv-research-copilot/
├── app/                                   # FastAPI backend
│   ├── core/                              # Core logic
│   │   ├── parsing.py                     # PDF parsing (PyMuPDF / pdfplumber)
│   │   ├── chunking.py                    # Heading-aware chunking
│   │   ├── embed.py                       # Embedding store (FAISS)
│   │   ├── retrieve.py                    # Retriever + CrossEncoder rerank
│   │   ├── prompts.py                     # Prompt templates (QA + JSON)
│   │   └── llm.py                         # LLM client (OpenAI / Ollama)
│   ├── routes/                            # API routes
│   │   ├── ingest.py                      # POST /ingest
│   │   ├── ask.py                         # POST /ask
│   │   └── extract.py                     # POST /extract
│   ├── schemas.py                         # Pydantic models (I/O)
│   └── deps.py                            # Paths, env, constants
├── ui/                                    # Streamlit frontend
│   └── app.py                             # Single-page UI (upload / ask / extract)
├── data/                                  # Local storage (gitignored)
│   ├── pdfs/                              # Uploaded PDFs
│   ├── store/                             # Parsed blocks / chunks
│   └── index/                             # FAISS index + metadata
├── .env.example                           # Example environment variables
├── requirements.txt                       # Python dependencies
├── Dockerfile                             # App image (FastAPI + Streamlit)
├── docker-compose.yml                     # Services: app + ollama (profiles)
├── assets/
│    └── demo.mp4                          # Demo video
└── README.md                              # You are here 
```

---

## Requirements

- **Python**: 3.11 (recommended; avoid 3.13 for native deps)
- **macOS**: Apple Silicon works great (tested on M-series)
- **Optional**: Docker & Docker Compose
- **Optional**: OpenAI API key (if not using local Ollama)

---

## Quickstart (Local, No Docker)

```bash
# 1) Clone
$ git clone https://github.com/yourname/cv-research-copilot.git
$ cd cv-research-copilot

# 2) Python env
$ python -m venv .venv && source .venv/bin/activate
$ pip install --upgrade pip
$ pip install -r requirements.txt

# 3) Configure env
$ cp .env.example .env
# (optional) set OPENAI_API_KEY=sk-...
# set USE_LOCAL=1 to force Ollama, or leave 0 to use OpenAI

# 4) Run backend
$ uvicorn app.main:app --host 0.0.0.0 --port 8000

# 5) Run UI
$ streamlit run ui/app.py --server.port 8501
```

- Backend: <http://localhost:8000>  
- API docs: <http://localhost:8000/docs>  
- UI: <http://localhost:8501>

**Optional (Streamlit secrets):** to change backend from the UI, create `~/.streamlit/secrets.toml`:

```toml
backend = "http://localhost:8000"
```

---

## Quickstart (Docker)

This repo uses Compose **profiles** to toggle local vs OpenAI modes.

### A) Local LLM (Ollama inside Compose)

```bash
# Build & start (app + ollama)
$ docker compose --profile local up -d --build

# Pull a model into the ollama container (first run only)
$ docker exec -it ollama ollama pull llama3.1
```

Open:
- UI: <http://localhost:8501>  
- API: <http://localhost:8000>

Check services:

```bash
$ docker compose --profile local ps
$ docker logs cv-research-copilot-app-1 --tail=200
$ docker logs ollama --tail=200
```

If the app can’t reach Ollama, exec into the app container and verify:

```bash
$ docker exec -it cv-research-copilot-app-1 bash -lc "apt-get update && apt-get install -y curl && curl -s http://ollama:11434/api/tags"
```

### B) OpenAI API Mode (no Ollama)

1) In `.env`:

```env
USE_LOCAL=0
OPENAI_API_KEY=<your key>
MODEL_PRIMARY=openai/gpt-4o-mini
```

2) Start the app profile:

```bash
$ docker compose --profile openai up -d --build
```

---

## Configuration

Create `.env` from `.env.example` and adjust as needed:

```env
# LLM routing
USE_LOCAL=1                        # 1 = use Ollama; 0 = use OpenAI
MODEL_LOCAL=ollama/llama3.1        # normalized to "llama3.1"
MODEL_PRIMARY=openai/gpt-4o-mini   # used when USE_LOCAL=0
OPENAI_API_KEY=                    # set if USE_LOCAL=0

# Embedding / rerank
EMBED_MODEL=BAAI/bge-m3
RERANK_MODEL=cross-encoder/ms-marco-MiniLM-L-6-v2
TOP_K=8

# Networking
API_PORT=8000
UI_PORT=8501
OLLAMA_BASE_URL=http://localhost:11434  # local dev; in Docker it's http://ollama:11434
```

---

## Usage

1. **Upload a PDF** on the *Ingest* tab, this parses, chunks, and indexes the paper.  
2. **Ask questions** on the *Ask* tab, this answers include `[p:##]` citations.  
3. **Extract JSON** on the *Extract JSON* tab, this returns normalized structured metadata.

**JSON schema (expected):**

```json
{
  "title": "Example Paper",
  "tasks": ["Object detection"],
  "methods": [
    {"name": "FPN", "components": ["Lateral connections"], "losses": ["Cross-entropy"]}
  ],
  "datasets": [{"name": "COCO", "split": "minival"}],
  "metrics": [{"dataset": "COCO", "metric": "mAP", "value": 36.2, "page": 5}],
  "ablations": [{"variable": "Backbone depth", "best_value": "ResNet-101"}]
}
```

**Tip:** The system is optimized for **computer vision** papers. Non-CV papers may produce sparser JSON until you expand prompts or context size.

---

## API Endpoints

- `GET /`  # health/info  
- `POST /ingest/` # upload & index a PDF  
- `POST /ask/` # ask a question about a doc  
- `POST /extract/` # extract structured JSON  
- **Docs:** <http://localhost:8000/docs>

---

## Stack

- **Backend:** FastAPI  
- **Frontend:** Streamlit  
- **Parsing:** PyMuPDF (text), pdfplumber (tables)  
- **Vector DB:** FAISS (cosine)  
- **Reranker:** CrossEncoder `ms-marco-MiniLM-L-6-v2`  
- **LLM:** OpenAI (e.g., `gpt-4o-mini`) or Ollama (`llama3.1`)  
- **Containers:** Docker + Compose (profiles)

---

## Troubleshooting

- **401 Unauthorized (OpenAI):** set `OPENAI_API_KEY` in `.env` or set `USE_LOCAL=1` to use Ollama.  
- **Ollama connection errors (Docker):**
  - Ensure the `ollama` container is **healthy** and a model is pulled:  
    `docker exec -it ollama ollama list`
  - From the app container, verify:  
    `curl -s http://ollama:11434/api/tags`
- **Model JSON not clean:** extraction route already strips code fences and normalizes fields. If you still see errors, try asking again or increase `TOP_K`.  
- **Python build issues:** use **Python 3.11** (avoid 3.13 which can break native deps).  
- **Health check:** `GET /` returns `{"ok": true, "service": "cv-research-copilot"}`.

---

## Roadmap / Ideas

- Paper-to-paper **diffing** (methods/datasets/metrics deltas)  
- Improved **table parsing** (images → table OCR)  
- **Evaluation harness** with a small gold set  
- Optional **vLLM** / **H100** “pro mode” (70B, long context)

---

## Contributing

1. Fork this repo  
2. Create a feature branch: `git checkout -b feat/my-feature`  
3. Commit & push: `git push origin feat/my-feature`  
4. Open a Pull Request 

---

## License

MIT © 2025 Agam Damaraju

---

**Acknowledgments:** Thanks to the authors & maintainers of PyMuPDF, pdfplumber, FAISS, SentenceTransformers, and the broader OSS community.
