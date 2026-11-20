"""Mistral chat-completions client (stdlib only) plus robust JSON extraction."""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request

DEFAULT_BASE_URL = "https://api.mistral.ai/v1"
DEFAULT_MODEL = "mistral-large-latest"


class LLMError(RuntimeError):
    pass


class MistralClient:
    """Minimal client for the Mistral chat completions API.

    The API key is read from the MISTRAL_API_KEY environment variable unless
    passed explicitly. The key is never logged or persisted.
    """

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        base_url: str | None = None,
        timeout: int = 90,
    ):
        self.api_key = api_key if api_key is not None else os.environ.get("MISTRAL_API_KEY", "")
        self.model = model or os.environ.get("CAREERFORGE_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.environ.get("CAREERFORGE_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout

    @property
    def available(self) -> bool:
        return bool(self.api_key)

    def chat(self, system: str, user: str, *, temperature: float = 0.5, max_tokens: int = 4096) -> str:
        if not self.available:
            raise LLMError(
                "MISTRAL_API_KEY is not set. Export your key from https://console.mistral.ai "
                "or run with --offline to use the built-in deterministic generator."
            )
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")[:500]
            raise LLMError(f"Mistral API error {exc.code}: {detail}") from exc
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise LLMError(f"could not reach Mistral API: {exc}") from exc
        try:
            return body["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LLMError(f"unexpected Mistral API response: {body!r:.300}") from exc


def extract_json(text: str) -> dict:
    """Extract the first JSON object from an LLM reply (fenced or raw)."""
    fenced = re.findall(r"```(?:json)?\s*(.*?)```", text, flags=re.DOTALL | re.IGNORECASE)
    candidates = fenced + [text]
    for candidate in candidates:
        candidate = candidate.strip()
        if not candidate.startswith("{"):
            start = candidate.find("{")
            if start == -1:
                continue
            candidate = candidate[start:]
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            parsed = _scan_balanced(candidate)
            if parsed is not None:
                return parsed
    raise LLMError("the model reply did not contain a valid JSON object")


def _scan_balanced(text: str):
    """Scan for a balanced {...} substring, respecting string literals."""
    depth = 0
    in_str = False
    escape = False
    start = None
    for i, ch in enumerate(text):
        if in_str:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None
