from __future__ import annotations
import requests, json, os, time

OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://ollama:11434")
OLLAMA_TIMEOUT_SEC = int(os.getenv("OLLAMA_TIMEOUT_SEC", "600"))
OLLAMA_RETRY = int(os.getenv("OLLAMA_RETRY", "6"))
OLLAMA_BACKOFF = float(os.getenv("OLLAMA_BACKOFF", "2.0"))

def _normalize_ollama_name(name: str) -> str:
    if not name:
        return "llama3.1"
    if name.startswith("ollama/"):
        name = name.split("/", 1)[1]
    return name  

class LLMClient:
    def __init__(self, primary, local, use_local, openai_key):
        self.primary = primary
        self.local = local
        self.use_local = use_local
        self.openai_key = openai_key

    def generate(self, system: str, user: str, expect_json: bool = False) -> str:
        if self.use_local:
            return self._ollama_generate(system, user, expect_json=expect_json)
        return self._openai_chat(system, user, expect_json)

    def _openai_chat(self, system: str, user: str, expect_json: bool) -> str:
        url = "https://api.openai.com/v1/chat/completions"
        key = self.openai_key
        if not key:
            raise RuntimeError("OPENAI_API_KEY not set")
        headers = {"Authorization": f"Bearer {key}", "Content-Type": "application/json"}
        model = (self.primary or "gpt-4o-mini").split("/", 1)[-1]
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}
        resp = requests.post(url, headers=headers, json=payload, timeout=120)
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"].strip()

    def _ollama_generate(self, system: str, user: str, expect_json: bool) -> str:
        model = _normalize_ollama_name(self.local or "llama3.1")
        self._ollama_ensure_model(model)

        prompt = f"System:\n{system}\n\nUser:\n{user}"
        url = f"{OLLAMA_BASE_URL}/api/generate"
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "3m",
            **({"format": "json"} if expect_json else {}),
        }

        last_exc = None
        for attempt in range(1, OLLAMA_RETRY + 1):
            try:
                r = requests.post(url, json=payload, timeout=OLLAMA_TIMEOUT_SEC)
                r.raise_for_status()
                data = r.json()
                return data.get("response", "").strip()
            except (requests.exceptions.ReadTimeout, requests.exceptions.ConnectionError) as e:
                last_exc = e
                time.sleep(OLLAMA_BACKOFF * attempt)
            except Exception:
                raise
        raise RuntimeError(f"Ollama generate failed after {OLLAMA_RETRY} attempts: {last_exc}")

    def _ollama_ensure_model(self, model: str) -> None:
        try:
            tags = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10).json()
            if any((m.get("name") or m.get("model") or "").split(":",1)[0] == model.split(":",1)[0]
                   for m in tags.get("models", [])):
                return
        except Exception:
            pass
        try:
            requests.post(f"{OLLAMA_BASE_URL}/api/pull", json={"name": model}, timeout=OLLAMA_TIMEOUT_SEC)
        except Exception:
            pass
        for _ in range(120):
            try:
                tags = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=10).json()
                if any((m.get("name") or m.get("model") or "").split(":",1)[0] == model.split(":",1)[0]
                       for m in tags.get("models", [])):
                    return
            except Exception:
                pass
            time.sleep(1)