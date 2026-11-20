from __future__ import annotations
import os
import httpx


class OllamaBackend:
    def __init__(self, model: str = "qwen2.5:3b", host: str = "http://localhost:11434"):
        self.model, self.host = model, host

    def complete(self, prompt: str) -> str:
        try:
            r = httpx.post(
                f"{self.host.rstrip('/')}/api/generate",
                json={"model": self.model, "prompt": prompt, "stream": False,
                      "options": {"temperature": 0.2}},
                timeout=120,
            )
            r.raise_for_status()
            return r.json()["response"]
        except Exception as e:
            raise RuntimeError(f"Ollama generation failed at {self.host} with model '{self.model}': {e}")


class ClaudeBackend:
    def __init__(self, model: str = "claude-sonnet-4-20250514"):
        self.model = model

    def complete(self, prompt: str) -> str:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("Claude backend requires ANTHROPIC_API_KEY environment variable")
        try:
            import anthropic
        except ImportError:
            # No SDK installed (e.g. the slim Vercel build): call the API directly over HTTPS.
            from ..tailor import call_claude
            return call_claude(prompt, self.model, api_key, max_tokens=4096)
        try:
            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model=self.model, max_tokens=4096,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text
        except Exception as e:
            raise RuntimeError(f"Claude API call failed: {e}")


class LiteLLMBackend:
    def __init__(self, model: str = "gpt-4o", api_key: str | None = None, api_base: str | None = None):
        self.model = model
        self.api_key = api_key
        self.api_base = api_base

    def complete(self, prompt: str) -> str:
        try:
            import litellm
            kwargs = {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key
            if self.api_base:
                kwargs["api_base"] = self.api_base
            resp = litellm.completion(**kwargs)
            return resp.choices[0].message.content or ""
        except ImportError:
            raise RuntimeError("LiteLLM backend requires 'litellm' package. Install with: pip install resume-builder[ai]")
        except Exception as e:
            raise RuntimeError(f"LiteLLM call failed with model '{self.model}': {e}")


class NoAIBackend:
    """Format only - does not invoke any LLM backend."""
    def complete(self, prompt: str) -> str:
        raise RuntimeError("NoAIBackend does not generate content")
