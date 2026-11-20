# src/resume_builder/ai/backends.py
import os
import httpx


class OllamaBackend:
    def __init__(self, model: str = "qwen2.5:3b", host: str = "http://localhost:11434"):
        self.model, self.host = model, host

    def complete(self, prompt: str) -> str:
        r = httpx.post(
            f"{self.host}/api/generate",
            json={"model": self.model, "prompt": prompt, "stream": False,
                  "options": {"temperature": 0.2}},
            timeout=120,
        )
        r.raise_for_status()
        return r.json()["response"]


class ClaudeBackend:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    def complete(self, prompt: str) -> str:
        import anthropic
        client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        msg = client.messages.create(
            model=self.model, max_tokens=4096,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text


class NoAIBackend:
    """不调用模型，直接把 master 原样返回，用于纯格式化导出。"""
    def complete(self, prompt: str) -> str:
        raise RuntimeError("NoAIBackend does not generate content")