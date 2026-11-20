"""Orchestration: run the three Mistral analyses and persist them in SQLite.

Each function loads the master profile + target, calls Mistral when an API key
is available (unless --offline), otherwise falls back to the deterministic
offline generator, validates the JSON, and stores it via Tracker.save_result.
"""

from __future__ import annotations

from careerforge import offline, prompts
from careerforge.llm import LLMError, MistralClient, extract_json

REQUIRED_KEYS = {
    "gap": ["match_score", "missing_skills", "missing_portfolio_proof", "transferable_strengths", "brutal_summary"],
    "project": ["title", "days", "final_deliverables", "demo_script"],
    "tailor": ["cv_bullets", "outreach"],
}


def _validate(kind: str, payload: dict) -> dict:
    if not isinstance(payload, dict):
        raise LLMError(f"{kind}: expected a JSON object, got {type(payload).__name__}")
    missing = [k for k in REQUIRED_KEYS[kind] if k not in payload]
    if missing:
        raise LLMError(f"{kind}: model output missing keys {missing}")
    if kind == "project":
        days = payload.get("days", [])
        if len(days) != 14:
            raise LLMError(f"project: expected exactly 14 days, got {len(days)}")
    return payload


def _run(kind: str, profile: dict, target: dict, client: MistralClient, use_offline: bool) -> tuple[dict, str, str]:
    """Returns (payload, mode, model). mode is 'llm' or 'offline'."""
    if use_offline or not client.available:
        generator = {"gap": offline.offline_gap_analysis, "project": offline.offline_project, "tailor": offline.offline_tailor}[kind]
        payload = generator(profile, target)
        _validate(kind, payload)
        return payload, "offline", "offline-heuristic"
    system, user = {
        "gap": prompts.gap_prompts,
        "project": prompts.project_prompts,
        "tailor": prompts.tailor_prompts,
    }[kind](profile, target)
    raw = client.chat(system, user, temperature=0.4 if kind != "tailor" else 0.6)
    payload = _validate(kind, extract_json(raw))
    return payload, "llm", client.model


def gap_analysis(tracker, target_id: int, client: MistralClient | None = None, offline_mode: bool = False) -> dict:
    target = tracker.get_target(target_id)
    if not target:
        raise LLMError(f"no target with id {target_id}")
    client = client or MistralClient()
    profile = tracker.get_profile()
    payload, mode, model = _run("gap", profile, target, client, offline_mode)
    payload["mode"] = mode
    tracker.save_result(target_id, "gap", payload, mode=mode, model=model)
    return tracker.get_latest_result(target_id, "gap")


def micro_project(tracker, target_id: int, client: MistralClient | None = None, offline_mode: bool = False) -> dict:
    target = tracker.get_target(target_id)
    if not target:
        raise LLMError(f"no target with id {target_id}")
    client = client or MistralClient()
    profile = tracker.get_profile()
    payload, mode, model = _run("project", profile, target, client, offline_mode)
    payload["mode"] = mode
    tracker.save_result(target_id, "project", payload, mode=mode, model=model)
    return tracker.get_latest_result(target_id, "project")


def tailor(tracker, target_id: int, client: MistralClient | None = None, offline_mode: bool = False) -> dict:
    target = tracker.get_target(target_id)
    if not target:
        raise LLMError(f"no target with id {target_id}")
    client = client or MistralClient()
    profile = tracker.get_profile()
    payload, mode, model = _run("tailor", profile, target, client, offline_mode)
    payload["mode"] = mode
    tracker.save_result(target_id, "tailor", payload, mode=mode, model=model)
    return tracker.get_latest_result(target_id, "tailor")


def run_all(tracker, target_id: int, client: MistralClient | None = None, offline_mode: bool = False) -> dict:
    return {
        "gap": gap_analysis(tracker, target_id, client, offline_mode),
        "project": micro_project(tracker, target_id, client, offline_mode),
        "tailor": tailor(tracker, target_id, client, offline_mode),
    }


def init_profile(tracker, raw_cv: str, name: str = "", client: MistralClient | None = None, offline_mode: bool = False) -> dict:
    """Build the master profile from raw CV text (LLM extraction or offline heuristic)."""
    from careerforge.profile import profile_from_cv_text

    client = client or MistralClient()
    if offline_mode or not client.available:
        profile = profile_from_cv_text(raw_cv, name=name)
        mode = "offline"
    else:
        system, user = prompts.profile_init_prompts(raw_cv)
        raw = client.chat(system, user, temperature=0.2)
        profile = extract_json(raw)
        profile["raw_cv"] = raw_cv
        if name:
            profile["name"] = name
        mode = "llm"
    profile["_init_mode"] = mode
    tracker.set_profile(profile)
    return tracker.get_profile()
