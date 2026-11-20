"""Master profile model: template, dotted-path editing, CV-based init."""

from __future__ import annotations

import json
import re
from pathlib import Path

PROFILE_TEMPLATE: dict = {
    "name": "",
    "contact": {"email": "", "phone": "", "address": "", "linkedin": "", "github": ""},
    "summary": "",
    "skills": [],  # e.g. [{"name": "Python", "level": "basic"}]
    "experience": [],  # e.g. [{"role": "", "company": "", "period": "", "bullets": []}]
    "education": [],
    "certifications": [],
    "projects": [],  # e.g. [{"title": "", "stack": [], "description": "", "link": ""}]
    "non_traditional_background": "",
    "languages": [],
    "work_preferences": {
        "roles": [],
        "locations": [],
        "remote": "",
        "employment_type": "",
        "salary_expectation": "",
        "industries": [],
    },
    "raw_cv": "",
}


def default_profile() -> dict:
    return json.loads(json.dumps(PROFILE_TEMPLATE))


def get_path(obj, path: str):
    """Read a dotted path like 'work_preferences.remote' or 'skills.0.name'."""
    cur = obj
    for key in path.split("."):
        if isinstance(cur, list):
            cur = cur[int(key)]
        elif isinstance(cur, dict):
            if key not in cur:
                raise KeyError(f"no such key: {path}")
            cur = cur[key]
        else:
            raise KeyError(f"cannot descend into {path!r} at {key!r}")
    return cur


def set_path(obj, path: str, value) -> None:
    """Set a dotted path, creating intermediate dicts. Use '-' to append to a list."""
    keys = path.split(".")
    cur = obj
    for key in keys[:-1]:
        if isinstance(cur, list):
            cur = cur[int(key)]
        else:
            nxt = cur.get(key)
            if not isinstance(nxt, (dict, list)):
                nxt = {}
                cur[key] = nxt
            cur = nxt
    last = keys[-1]
    if isinstance(cur, list):
        if last == "-":
            cur.append(value)
        else:
            idx = int(last)
            while len(cur) <= idx:
                cur.append(None)
            cur[idx] = value
    else:
        cur[last] = value


def parse_value(raw: str):
    """Parse a CLI value as JSON when possible, else keep it as a string."""
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
_PHONE_RE = re.compile(r"\+?\d[\d\s()/.-]{6,}\d")


def profile_from_cv_text(cv_text: str, name: str = "") -> dict:
    """Deterministic offline extraction of a starter profile from plain-text CV.

    The LLM path (see engine.init_profile) produces a much richer structure;
    this heuristic version only guarantees the basics so the app is usable
    without an API key.
    """
    profile = default_profile()
    profile["raw_cv"] = cv_text
    if name:
        profile["name"] = name
    emails = _EMAIL_RE.findall(cv_text)
    if emails:
        profile["contact"]["email"] = emails[0]
    phones = [p.strip() for p in _PHONE_RE.findall(cv_text)]
    if phones:
        profile["contact"]["phone"] = phones[0]
    if not profile["summary"]:
        profile["summary"] = (
            "Profile initialised from CV text. Edit with: careerforge profile set <path> <value>"
        )
    return profile


def load_profile_file(path: str | Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def dump_profile_file(profile: dict, path: str | Path) -> None:
    Path(path).write_text(json.dumps(profile, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
