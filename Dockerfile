# syntax=docker/dockerfile:1.7
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    STREAMLIT_BROWSER_GATHERUSAGESTATS=false \
    API_PORT=8000 \
    UI_PORT=8501

RUN apt-get update && apt-get install -y --no-install-recommends libgl1 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY ui ./ui
COPY .env.example ./.env.example

RUN mkdir -p data/pdfs data/store data/index

EXPOSE 8000 8501

CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${API_PORT} & \
           streamlit run ui/app.py --server.port ${UI_PORT} --server.address 0.0.0.0"