# CV Research Copilot (LLM)

Upload a CV paper PDF →
- Ask **natural language questions** with **page citations** like `[p:12]`.
- Extract a **strict JSON** of Methods / Datasets / Metrics / Ablations (with page refs for every number).
- Compare papers (basic diff via two runs).

## Quickstart (MacBook Pro M4)

### 1. Clone & Install
```bash
python -m venv .venv && source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt