import requests, json

class LLMClient:
    def __init__(self, primary: str, local: str, use_local: bool = False, api_key: str = ""):
        self.primary = primary  # e.g., "openai/gpt-4o-mini"
        self.local = local      # e.g., "ollama/llama3.1:8b-instruct"
        self.use_local = use_local
        self.api_key = api_key

    def generate(self, system: str, user: str, expect_json: bool = False) -> str:
        if self.use_local:
            return self._ollama_generate(system, user)
        if self.primary.startswith("openai/"):
            return self._openai_chat(system, user, expect_json)
        return self._openai_chat(system, user, expect_json)

    def _openai_chat(self, system: str, user: str, expect_json: bool) -> str:
        model = self.primary.split("/", 1)[1]
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.1,
        }
        if expect_json:
            payload["response_format"] = {"type": "json_object"}
        r = requests.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload, timeout=120)
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()

    def _ollama_generate(self, system: str, user: str) -> str:
        model = self.local.split("/", 1)[1]
        prompt = f"SYSTEM:\n{system}\n\nUSER:\n{user}"
        r = requests.post(
            "http://localhost:11434/api/generate",
            json={"model": model, "prompt": prompt, "stream": False},
        )
        r.raise_for_status()
        return r.json().get("response", "").strip()