"""Target ingestion: job descriptions from text/files/URLs and company pages."""

from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser

MAX_FETCH_CHARS = 12000
USER_AGENT = "careerforge/0.1 (+local career tool)"

JD_HINTS = [
    "responsibilit", "requirements", "qualifications", "what you'll do", "what you will do",
    "požadujeme", " requirements", "we are looking for", "we're looking for", "your profile",
    "benefits", "we offer", "náš tím",
]


class FetchError(RuntimeError):
    pass


class _TextExtractor(HTMLParser):
    _SKIP = {"script", "style", "noscript", "svg", "head"}

    def __init__(self):
        super().__init__()
        self.parts: list[str] = []
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in self._SKIP:
            self._skip += 1

    def handle_endtag(self, tag):
        if tag in self._SKIP and self._skip > 0:
            self._skip -= 1

    def handle_data(self, data):
        if self._skip == 0:
            text = data.strip()
            if text:
                self.parts.append(text)


def html_to_text(html: str) -> str:
    parser = _TextExtractor()
    parser.feed(html)
    text = "\n".join(parser.parts)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def fetch_url(url: str, timeout: int = 20) -> str:
    """Fetch a URL and return readable text (best effort)."""
    if not re.match(r"^https?://", url):
        raise FetchError(f"not an http(s) URL: {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html,text/plain,*/*"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(MAX_FETCH_CHARS * 4)
    except Exception as exc:  # network errors are expected to be handled by callers
        raise FetchError(f"could not fetch {url}: {exc}") from exc
    charset = "utf-8"
    content_type = resp.headers.get("Content-Type", "") if hasattr(resp, "headers") else ""
    m = re.search(r"charset=([\w-]+)", content_type)
    if m:
        charset = m.group(1)
    try:
        html = raw.decode(charset, errors="replace")
    except LookupError:
        html = raw.decode("utf-8", errors="replace")
    if "<html" in html.lower() or "<body" in html.lower():
        html = html_to_text(html)
    return html[:MAX_FETCH_CHARS]


def looks_like_job_description(text: str) -> bool:
    lowered = text.lower()
    return sum(1 for hint in JD_HINTS if hint in lowered) >= 2


def load_jd(source: str, is_url: bool = False) -> str:
    """Load a job description from inline text, a file path, or a URL."""
    if is_url:
        return fetch_url(source)
    from pathlib import Path

    path = Path(source)
    if path.exists() and path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    return source
