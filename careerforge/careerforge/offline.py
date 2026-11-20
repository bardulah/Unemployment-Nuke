"""Deterministic offline generators.

Used when MISTRAL_API_KEY is not set or --offline is passed. Output follows the
exact same JSON schemas as the LLM prompts, and every result is marked
"mode": "offline" so it is never mistaken for model output.
"""

from __future__ import annotations

import re

SKILL_LEXICON = [
    "python", "sql", "excel", "pandas", "numpy", "tableau", "power bi", "looker", "excel formulas",
    "vba", "aws", "azure", "gcp", "docker", "kubernetes", "linux", "bash", "networking", "tcp/ip",
    "dns", "dhcp", "active directory", "windows server", "jira", "confluence", "git", "github",
    "html", "css", "javascript", "flask", "django", "fastapi", "rest api", "api", "etl", "elt",
    "data analysis", "data analytics", "machine learning", "statistics", "a/b testing", "agile",
    "scrum", "kanban", "itsm", "ITIL", "ticketing", "helpdesk", "service desk", "customer support",
    "zendesk", "freshdesk", "logistics", "customs", "taric", "hs code", "invoicing", "warehouse",
    "wms", "sap", "erp", "cms", "e-commerce", "excel vba", "automation", "web scraping",
    "beautifulsoup", "selenium", "postgresql", "mysql", "sqlite", "data cleaning", "visualization",
    "excel pivot", "pivot tables", "vlookup", "powerpoint", "word",
]

_BANNED_TAILOR_WORDS = [
    "passionate", "synergy", "hard-working", "team player", "fast learner",
    "results-driven", "guru", "ninja", "rockstar", "self-starter", "detail-oriented",
]


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower())


def _profile_text(profile: dict) -> str:
    import json

    return _norm(json.dumps(profile, ensure_ascii=False))


def _jd_text(target: dict) -> str:
    return _norm(target.get("jd_text", "") + "\n" + target.get("company_context", ""))


def _profile_skill_names(profile: dict) -> set[str]:
    names = set()
    for skill in profile.get("skills", []) or []:
        if isinstance(skill, dict):
            names.add(_norm(skill.get("name", "")))
        else:
            names.add(_norm(str(skill)))
    return {n for n in names if n}


def offline_gap_analysis(profile: dict, target: dict) -> dict:
    jd = _jd_text(target)
    have = _profile_text(profile)
    have_skills = _profile_skill_names(profile)

    missing_skills, missing_proof = [], []
    for term in SKILL_LEXICON:
        if term in jd and term not in have and term not in have_skills:
            missing_skills.append({
                "skill": term,
                "required_by": f"mentioned in the {target.get('title') or 'target'} posting",
                "current_level": "none",
                "how_to_close": f"build one small deliverable that uses {term} and link it in the CV/portfolio",
            })
    if not missing_skills:
        missing_skills.append({
            "skill": "role-specific domain knowledge",
            "required_by": target.get("title") or "target role",
            "current_level": "basic",
            "how_to_close": "map 3 real tasks from the JD to things you already did in past roles",
        })
    missing_proof.append({
        "proof": "public portfolio project tied to this company's problem",
        "why": "recruiters cannot verify claims from a CV alone",
        "how_to_build": "run `careerforge project <id>` to generate a 14-day micro-project spec, then build it",
    })

    strengths_pool = [
        ("process documentation & data accuracy",
         "years of order processing, invoicing and customs documentation",
         "frame as data-entry quality and audit-ready documentation — the same discipline data teams need"),
        ("cross-team coordination",
         "supplier, courier, client and customs-authority communication",
         "frame as stakeholder management and clear written communication"),
        ("self-directed upskilling",
         "IT support certificate + Python bootcamp completed alongside full-time work",
         "frame as proof you can learn technical tooling independently and ship it"),
        ("analytical thinking",
         "explicitly listed skill, backed by HS/TARIC classification work",
         "frame as structured problem solving: classify, verify, resolve"),
    ]
    transferable = [{"strength": s, "evidence": e, "framing": f} for s, e, f in strengths_pool]

    score = max(10, min(90, 55 + 5 * len([t for t in SKILL_LEXICON if t in have and t in jd]) - 8 * len(missing_skills)))
    return {
        "match_score": score,
        "one_line_verdict": (
            f"Offline estimate: partial fit for {target.get('title') or 'this role'} — "
            f"{len(missing_skills)} skill gap(s) to close before applying."
        ),
        "missing_skills": missing_skills[:8],
        "missing_portfolio_proof": missing_proof,
        "transferable_strengths": transferable,
        "red_flags": [
            "No formal degree completed — expect screening questions about education",
            "No public portfolio yet — CV claims are unverifiable until you ship one project",
        ],
        "quick_wins": [
            {"action": "Generate and start the 14-day micro-project for this target", "effort_days": 14},
            {"action": "Rewrite CV bullets for this role with `careerforge tailor <id>`", "effort_days": 1},
            {"action": "List the 3 closest matching skills from past roles in the CV skills section", "effort_days": 1},
        ],
        "brutal_summary": (
            "Offline mode: this is a keyword-overlap estimate, not a model judgement. "
            "The real gaps are portfolio proof and role-specific tooling. Build the micro-project "
            "first, then apply — a link beats a promise. Set MISTRAL_API_KEY for the full analysis."
        ),
    }


def offline_project(profile: dict, target: dict) -> dict:
    role = target.get("title") or "target role"
    company = target.get("company") or "the target company"
    jd = _jd_text(target)
    stack = [t for t in ["python", "sql", "pandas", "excel", "git", "rest api", "docker", "linux"] if t in jd][:5] or ["python", "git"]
    return {
        "title": f"{role} proof-of-work for {company}".strip(),
        "target_role": role,
        "company_problem": (
            f"From the {role} posting at {company}: the team needs someone who can turn messy "
            "operational data into reliable, documented answers — the same class of problem as "
            "order/customs data processing, but expressed in code."
        ),
        "why_this_proves_fit": (
            "It mirrors the role's core loop: take unclear input, structure it, verify it, "
            "deliver a documented result others can trust."
        ),
        "stack": stack,
        "repo_structure": [
            "README.md — problem, approach, results",
            "data/ — small sample dataset (public or synthetic)",
            "src/ — clean, tested Python code",
            "notebooks/ or analysis.py — reproducible analysis",
            "tests/ — pytest tests proving correctness",
            "DEMO.md — 3-minute demo script",
        ],
        "days": [
            {"day": 1, "focus": "Scope", "tasks": ["Pick one concrete question the company cares about", "Write the problem statement in 3 sentences"], "deliverable": "README problem statement"},
            {"day": 2, "focus": "Data", "tasks": ["Find or synthesize a small realistic dataset", "Document its source and quirks"], "deliverable": "data/ with a data dictionary"},
            {"day": 3, "focus": "Clean", "tasks": ["Handle missing values, duplicates, type errors", "Log every cleaning decision"], "deliverable": "reproducible cleaning script"},
            {"day": 4, "focus": "Clean", "tasks": ["Write the first pytest tests for the cleaning code"], "deliverable": "passing tests"},
            {"day": 5, "focus": "Explore", "tasks": ["Answer the day-1 question with the cleaned data", "Note 2-3 insights a hiring manager would care about"], "deliverable": "analysis output + notes"},
            {"day": 6, "focus": "Explore", "tasks": ["Build one clear visualization or summary table"], "deliverable": "chart/table saved to repo"},
            {"day": 7, "focus": "Package", "tasks": ["Turn the notebook into a runnable script (src/)", "Add CLI entry point"], "deliverable": "python -m src.main works"},
            {"day": 8, "focus": "Automate", "tasks": ["Add a small automation: scheduled run, or one API fetch, or one Excel/CSV export"], "deliverable": "automation snippet + explanation"},
            {"day": 9, "focus": "Tests", "tasks": ["Reach meaningful test coverage on core logic", "Add a CI badge (GitHub Actions)"], "deliverable": "green CI"},
            {"day": 10, "focus": "Polish code", "tasks": ["Refactor, type hints, docstrings, lint clean"], "deliverable": "clean, readable codebase"},
            {"day": 11, "focus": "README", "tasks": ["Follow the readme_outline: problem, approach, results, how to run"], "deliverable": "complete README"},
            {"day": 12, "focus": "Demo", "tasks": ["Write DEMO.md 3-minute walkthrough", "Record or script the demo"], "deliverable": "demo script"},
            {"day": 13, "focus": "Metrics", "tasks": ["Define success_metrics and measure them", "Add results to README"], "deliverable": "measured results"},
            {"day": 14, "focus": "Ship", "tasks": ["Publish repo publicly", "Pin the link in CV, LinkedIn and outreach"], "deliverable": "public repo URL"},
        ],
        "final_deliverables": ["public GitHub repo", "README with problem/approach/results", "passing tests + CI", "3-minute demo script"],
        "readme_outline": ["Problem", "Data", "Approach", "Results", "How to run", "What I'd do next"],
        "demo_script": [
            "Show the repo in 10 seconds",
            "Run the pipeline live in 60 seconds",
            "Show one insight and one test passing",
            "Close with what this proves about working style",
        ],
        "success_metrics": ["repo has passing CI", "README answers 'why should we hire you' in 30 seconds", "demo runs end-to-end without errors"],
    }


def offline_tailor(profile: dict, target: dict) -> dict:
    role = target.get("title") or "this role"
    company = target.get("company") or "your company"
    exp = profile.get("experience", []) or []
    bullets = []
    for job in exp[:3]:
        role_name = job.get("role", "Role")
        for b in (job.get("bullets", []) or [])[:2]:
            verb = re.sub(r"[^\w\s-]", "", b).strip().split(" ")[0] or "Handled"
            bullets.append({
                "section": f"{role_name} — {job.get('company', '')}".strip(" —"),
                "bullets": [f"{verb.capitalize()} {b[0].lower() + b[1:]} — framed for {role}: reliable, documented, audit-ready work at operational scale."],
            })
    if not bullets:
        bullets = [{"section": "Experience", "bullets": ["Reframe your strongest responsibility as: verb + object + outcome."]}]
    skills = [s.get("name", str(s)) if isinstance(s, dict) else str(s) for s in (profile.get("skills", []) or [])][:8]
    name = profile.get("name") or "the candidate"
    return {
        "cv_summary": (
            f"Operations and logistics professional transitioning into {role}. "
            "Brings audit-grade documentation habits, cross-team coordination and self-taught "
            "technical skills (IT support certificate, Python), plus a shipped portfolio project."
        ),
        "cv_bullets": bullets,
        "skills_section": skills or ["Python", "SQL", "Excel", "Documentation", "Stakeholder communication"],
        "outreach": {
            "subject": f"{role} — operational rigour meets shipped code",
            "email_body": (
                f"Hi,\n\nI'm applying for the {role} role at {company}. My background is in operations "
                f"and customs documentation, where accuracy and clear documentation were the job — "
                f"the same discipline this role needs.\n\nOn the side I completed an IT support "
                f"certificate and a Python bootcamp, and I shipped a small end-to-end project "
                f"(public repo, tests, demo) that mirrors how I'd approach your team's day-to-day work: "
                f"take messy input, structure it, verify it, document it.\n\nHappy to walk you through the "
                f"project in a 15-minute call.\n\nBest regards,\n{name}"
            ),
            "linkedin_dm": (
                f"Hi — I applied for {role} at {company}. Quick context: operations/customs background, "
                f"plus a shipped Python project with tests and a demo. Could I get 15 minutes to show "
                f"how I'd approach your team's workflows?"
            ),
            "tips": ["Replace the project mention with your real repo link", "Name one specific product/team of the company", "Send Tuesday-Thursday morning"],
        },
    }
