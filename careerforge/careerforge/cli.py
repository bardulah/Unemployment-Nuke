"""careerforge command line interface."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from careerforge import engine, profile as profile_mod, targets as targets_mod
from careerforge.db import APPLICATION_STATUSES, Tracker, today
from careerforge.llm import LLMError, MistralClient

DEFAULT_DATA_DIR = os.environ.get("CAREERFORGE_DATA_DIR") or str(Path.home() / ".careerforge")


def get_tracker(args) -> Tracker:
    return Tracker(args.data_dir)


def get_client(args) -> MistralClient:
    return MistralClient(model=getattr(args, "model", None))


def use_offline(args) -> bool:
    return bool(getattr(args, "offline", False)) or os.environ.get("CAREERFORGE_OFFLINE") == "1"


# --------------------------------------------------------------------- renderers
def render_gap(result: dict) -> str:
    p = result["payload"]
    lines = [
        f"GAP ANALYSIS  (mode={result['mode']}, model={result['model']}, {result['created_at']})",
        f"Match score: {p.get('match_score')}/100",
        f"Verdict: {p.get('one_line_verdict', '')}",
        "",
        "MISSING SKILLS:",
    ]
    for s in p.get("missing_skills", []):
        lines.append(f"  - {s.get('skill')} (now: {s.get('current_level')}) — close via: {s.get('how_to_close')}")
    lines.append("")
    lines.append("MISSING PORTFOLIO PROOF:")
    for s in p.get("missing_portfolio_proof", []):
        lines.append(f"  - {s.get('proof')} — build via: {s.get('how_to_build')}")
    lines.append("")
    lines.append("TRANSFERABLE STRENGTHS:")
    for s in p.get("transferable_strengths", []):
        lines.append(f"  - {s.get('strength')} [{s.get('evidence')}] -> pitch as: {s.get('framing')}")
    if p.get("red_flags"):
        lines.append("")
        lines.append("RED FLAGS:")
        lines += [f"  - {r}" for r in p["red_flags"]]
    if p.get("quick_wins"):
        lines.append("")
        lines.append("QUICK WINS:")
        lines += [f"  - {q.get('action')} (~{q.get('effort_days')}d)" for q in p["quick_wins"]]
    lines += ["", "BRUTAL SUMMARY:", p.get("brutal_summary", "")]
    return "\n".join(lines)


def render_project(result: dict) -> str:
    p = result["payload"]
    lines = [
        f"14-DAY MICRO-PROJECT  (mode={result['mode']}, model={result['model']})",
        f"Title: {p.get('title')}",
        f"Company problem: {p.get('company_problem')}",
        f"Why it proves fit: {p.get('why_this_proves_fit')}",
        f"Stack: {', '.join(p.get('stack', []))}",
        "",
        "DAY-BY-DAY:",
    ]
    for d in p.get("days", []):
        lines.append(f"  Day {d.get('day')}: {d.get('focus')}")
        for t in d.get("tasks", []):
            lines.append(f"      - {t}")
        lines.append(f"      => {d.get('deliverable')}")
    lines += ["", "FINAL DELIVERABLES:"] + [f"  - {x}" for x in p.get("final_deliverables", [])]
    lines += ["", "DEMO SCRIPT:"] + [f"  - {x}" for x in p.get("demo_script", [])]
    lines += ["", "SUCCESS METRICS:"] + [f"  - {x}" for x in p.get("success_metrics", [])]
    return "\n".join(lines)


def render_tailor(result: dict) -> str:
    p = result["payload"]
    lines = [
        f"TAILORED CV + OUTREACH  (mode={result['mode']}, model={result['model']})",
        "",
        "CV SUMMARY:",
        p.get("cv_summary", ""),
        "",
        "CV BULLETS:",
    ]
    for section in p.get("cv_bullets", []):
        lines.append(f"  [{section.get('section')}]")
        lines += [f"    - {b}" for b in section.get("bullets", [])]
    if p.get("skills_section"):
        lines += ["", "SKILLS SECTION:", "  " + ", ".join(p["skills_section"])]
    out = p.get("outreach", {})
    lines += [
        "",
        "OUTREACH:",
        f"  Subject: {out.get('subject', '')}",
        "",
        out.get("email_body", ""),
        "",
        "LinkedIn DM:",
        out.get("linkedin_dm", ""),
    ]
    if out.get("tips"):
        lines += ["", "TIPS:"] + [f"  - {t}" for t in out["tips"]]
    return "\n".join(lines)


# ------------------------------------------------------------------------ export
def export_target(tracker: Tracker, target_id: int, out_dir: str | Path) -> list[Path]:
    target = tracker.get_target(target_id)
    if not target:
        raise LLMError(f"no target with id {target_id}")
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    base = (target.get("company") or target["title"]).lower()
    slug = "".join(c if c.isalnum() else "-" for c in base).strip("-") or f"target-{target_id}"
    written = []
    for kind, renderer, suffix in [
        ("gap", render_gap, "gap-analysis"),
        ("project", render_project, "14day-project"),
        ("tailor", render_tailor, "tailored-cv-outreach"),
    ]:
        result = tracker.get_latest_result(target_id, kind)
        if result:
            f = out / f"{slug}-{suffix}.md"
            f.write_text(f"# {kind.title()} — {target['title']}\n\n" + renderer(result) + "\n", encoding="utf-8")
            written.append(f)
    f = out / f"{slug}-jd.md"
    f.write_text(f"# Target — {target['title']}\n\n" + (target.get("jd_text") or "") + "\n", encoding="utf-8")
    written.append(f)
    return written


# --------------------------------------------------------------------------- CLI
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="careerforge",
        description="Career strategy & portfolio builder: gap analysis, 14-day micro-projects, "
        "tailored CV/outreach (Mistral-powered) + SQLite application tracker and local dashboard.",
    )
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                        help="where the SQLite DB lives (default: $CAREERFORGE_DATA_DIR or ~/.careerforge)")
    parser.add_argument("--offline", action="store_true",
                        help="never call the Mistral API; use the built-in deterministic generator")
    parser.add_argument("--model", default=None, help="Mistral model (default: $CAREERFORGE_MODEL or mistral-large-latest)")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("profile", help="manage the master profile")
    psub = p.add_subparsers(dest="action", required=True)
    pi = psub.add_parser("init", help="create the profile from plain-text CV")
    pi.add_argument("--from-cv", required=True, help="path to a plain-text/markdown CV")
    pi.add_argument("--name", default="")
    pshow = psub.add_parser("show", help="print the profile")
    pshow.add_argument("--json", action="store_true", help="raw JSON only")
    ps = psub.add_parser("set", help="set a dotted path, e.g. careerforge profile set work_preferences.remote hybrid")
    ps.add_argument("path", help="dotted path; use '-' as last segment to append to a list")
    ps.add_argument("value", help="value (parsed as JSON when possible)")
    psub.add_parser("import", help="replace profile from a JSON file").add_argument("file")
    psub.add_parser("export", help="dump profile to a JSON file").add_argument("file")

    t = sub.add_parser("target", help="manage target roles")
    tsub = t.add_subparsers(dest="action", required=True)
    ta = tsub.add_parser("add", help="add a target role from a JD and/or company URL")
    ta.add_argument("--title", required=True)
    ta.add_argument("--company", default="")
    ta.add_argument("--url", default="", help="company URL (fetched as company context)")
    ta.add_argument("--jd-url", default="", help="URL of the job posting itself")
    ta.add_argument("--jd-file", default="", help="local file with the job description")
    ta.add_argument("--jd", default="", help="inline job description text")
    ta.add_argument("--location", default="")
    ta.add_argument("--notes", default="")
    tsub.add_parser("list", help="list targets")
    ts = tsub.add_parser("show", help="show one target")
    ts.add_argument("id", type=int)
    tdel = tsub.add_parser("delete", help="delete a target and its results")
    tdel.add_argument("id", type=int)

    for name, help_text in [
        ("analyze", "brutal gap analysis for a target"),
        ("project", "generate the 14-day micro-project spec"),
        ("tailor", "tailor CV bullets + outreach"),
        ("run", "analyze + project + tailor in one go"),
    ]:
        c = sub.add_parser(name, help=help_text)
        c.add_argument("target_id", type=int)

    ex = sub.add_parser("export", help="export generated markdown files for a target")
    ex.add_argument("target_id", type=int)
    ex.add_argument("--out", required=True, help="output directory")

    tr = sub.add_parser("track", help="application tracker")
    trsub = tr.add_subparsers(dest="action", required=True)
    tra = trsub.add_parser("add", help="log an application")
    tra.add_argument("--target", type=int, default=None, help="target id")
    tra.add_argument("--title", default="", help="role title (for ad-hoc applications)")
    tra.add_argument("--company", default="")
    tra.add_argument("--status", default="saved", choices=APPLICATION_STATUSES)
    tra.add_argument("--contact", default="")
    tra.add_argument("--applied-at", default="", help="YYYY-MM-DD")
    tra.add_argument("--followup", default="", help="next follow-up date YYYY-MM-DD")
    tra.add_argument("--note", default="")
    trsub.add_parser("list", help="list applications")
    trs = trsub.add_parser("set", help="update an application")
    trs.add_argument("id", type=int)
    trs.add_argument("--status", choices=APPLICATION_STATUSES)
    trs.add_argument("--contact")
    trs.add_argument("--followup")
    trs.add_argument("--note")

    r = sub.add_parser("remind", help="follow-up reminders")
    rsub = r.add_subparsers(dest="action", required=True)
    ra = rsub.add_parser("add", help="add a reminder")
    ra.add_argument("--message", required=True)
    ra.add_argument("--due", required=True, help="YYYY-MM-DD")
    ra.add_argument("--app", type=int, default=None, help="application id to link")
    rl = rsub.add_parser("list", help="list reminders (use --all to include done)")
    rl.add_argument("--all", action="store_true")
    rl.add_argument("--due", action="store_true", help="only reminders due today or earlier")
    rd = rsub.add_parser("done", help="mark a reminder done")
    rd.add_argument("id", type=int)

    sub.add_parser("status", help="overview of profile, targets, applications, reminders")

    sv = sub.add_parser("serve", help="start the local web dashboard (loopback only by default)")
    sv.add_argument("--host", default="127.0.0.1")
    sv.add_argument("--port", type=int, default=8000)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return dispatch(args)
    except (LLMError, ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2


def dispatch(args) -> int:
    if args.command == "profile":
        return cmd_profile(args)
    if args.command == "target":
        return cmd_target(args)
    if args.command in ("analyze", "project", "tailor", "run"):
        return cmd_generate(args)
    if args.command == "export":
        with get_tracker(args) as tr:
            written = export_target(tr, args.target_id, args.out)
        for f in written:
            print(f"wrote {f}")
        return 0
    if args.command == "track":
        return cmd_track(args)
    if args.command == "remind":
        return cmd_remind(args)
    if args.command == "status":
        return cmd_status(args)
    if args.command == "serve":
        from careerforge.web import serve

        serve(args.data_dir, host=args.host, port=args.port)
        return 0
    raise ValueError(f"unknown command {args.command}")


def cmd_profile(args) -> int:
    with get_tracker(args) as tr:
        if args.action == "init":
            raw_cv = Path(args.from_cv).read_text(encoding="utf-8", errors="replace")
            prof = engine.init_profile(tr, raw_cv, name=args.name, client=get_client(args), offline_mode=use_offline(args))
            print(f"profile initialised (mode={prof.get('_init_mode', '?')}). Edit with: careerforge profile set <path> <value>")
            return 0
        if args.action == "show":
            prof = tr.get_profile()
            if args.json:
                print(json.dumps(prof, ensure_ascii=False, indent=2))
            else:
                print(json.dumps(prof, ensure_ascii=False, indent=2))
            return 0
        if args.action == "set":
            prof = tr.get_profile() or profile_mod.default_profile()
            profile_mod.set_path(prof, args.path, profile_mod.parse_value(args.value))
            tr.set_profile(prof)
            print(f"set {args.path}")
            return 0
        if args.action == "import":
            tr.set_profile(profile_mod.load_profile_file(args.file))
            print(f"imported profile from {args.file}")
            return 0
        if args.action == "export":
            profile_mod.dump_profile_file(tr.get_profile(), args.file)
            print(f"exported profile to {args.file}")
            return 0
    return 0


def cmd_target(args) -> int:
    if args.action == "add":
        jd_text = ""
        company_context = ""
        if args.jd:
            jd_text = args.jd
        if args.jd_file:
            jd_text = targets_mod.load_jd(args.jd_file)
        if args.jd_url:
            try:
                jd_text = targets_mod.fetch_url(args.jd_url)
            except targets_mod.FetchError as exc:
                print(f"warning: {exc}", file=sys.stderr)
        if args.url:
            try:
                company_context = targets_mod.fetch_url(args.url)
                if targets_mod.looks_like_job_description(company_context) and not jd_text:
                    jd_text, company_context = company_context, ""
            except targets_mod.FetchError as exc:
                print(f"warning: {exc}", file=sys.stderr)
        if not jd_text and not company_context:
            raise ValueError("provide at least one of --jd, --jd-file, --jd-url, --url")
        with get_tracker(args) as tr:
            tid = tr.add_target(
                title=args.title, company=args.company, url=args.url or args.jd_url, location=args.location,
                jd_text=jd_text, company_context=company_context, notes=args.notes,
            )
        print(f"target #{tid}: {args.title}" + (f" @ {args.company}" if args.company else ""))
        return 0
    with get_tracker(args) as tr:
        if args.action == "list":
            rows = tr.list_targets()
            stats = tr.stats()["match_scores"]
            if not rows:
                print("no targets yet. Add one: careerforge target add --title ... --jd-file jd.txt")
                return 0
            for t in rows:
                score = stats.get(t["id"])
                score_s = f"  match={score}" if score is not None else ""
                print(f"#{t['id']}  {t['title']} @ {t['company']} ({t['location']}){score_s}  jd={len(t['jd_text'])} chars")
            return 0
        if args.action == "show":
            t = tr.get_target(args.id)
            if not t:
                raise ValueError(f"no target with id {args.id}")
            print(json.dumps(t, ensure_ascii=False, indent=2))
            return 0
        if args.action == "delete":
            tr.delete_target(args.id)
            print(f"deleted target #{args.id}")
            return 0
    return 0


def cmd_generate(args) -> int:
    with get_tracker(args) as tr:
        client = get_client(args)
        off = use_offline(args)
        tid = args.target_id
        if args.command == "analyze":
            print(render_gap(engine.gap_analysis(tr, tid, client, off)))
        elif args.command == "project":
            print(render_project(engine.micro_project(tr, tid, client, off)))
        elif args.command == "tailor":
            print(render_tailor(engine.tailor(tr, tid, client, off)))
        elif args.command == "run":
            results = engine.run_all(tr, tid, client, off)
            print(render_gap(results["gap"]))
            print()
            print(render_project(results["project"]))
            print()
            print(render_tailor(results["tailor"]))
    return 0


def cmd_track(args) -> int:
    with get_tracker(args) as tr:
        if args.action == "add":
            target = tr.get_target(args.target) if args.target else None
            title = args.title or (target["title"] if target else "")
            company = args.company or (target["company"] if target else "")
            app_id = tr.add_application(
                status=args.status, target_id=args.target, role_title=title, company=company,
                contact=args.contact, applied_at=args.applied_at or (today() if args.status != "saved" else ""),
                next_followup=args.followup, notes=args.note,
            )
            print(f"application #{app_id}: {title} @ {company} [{args.status}]")
            return 0
        if args.action == "list":
            rows = tr.list_applications()
            if not rows:
                print("no applications yet. Log one: careerforge track add --target 1 --status applied")
                return 0
            for a in rows:
                title = a.get("target_title") or a["role_title"]
                company = a["company"]
                follow = f"  follow-up: {a['next_followup']}" if a["next_followup"] else ""
                print(f"#{a['id']}  [{a['status']:<10}] {title} @ {company}{follow}  contact={a['contact'] or '-'}")
                if a["notes"]:
                    print(f"    note: {a['notes']}")
            return 0
        if args.action == "set":
            tr.update_application(args.id, status=args.status, contact=args.contact,
                                  next_followup=args.followup, notes=args.note)
            print(f"updated application #{args.id}")
            return 0
    return 0


def cmd_remind(args) -> int:
    with get_tracker(args) as tr:
        if args.action == "add":
            rid = tr.add_reminder(args.message, args.due, application_id=args.app)
            print(f"reminder #{rid}: {args.message} (due {args.due})")
            return 0
        if args.action == "list":
            rows = tr.due_reminders() if args.due else tr.list_reminders(include_done=args.all)
            if not rows:
                print("no reminders" + (" due" if args.due else ""))
                return 0
            for r in rows:
                mark = "x" if r["done"] else " "
                print(f"[{mark}] #{r['id']}  due {r['due_date']}  {r['message']}" + (f"  (app #{r['application_id']})" if r["application_id"] else ""))
            return 0
        if args.action == "done":
            tr.complete_reminder(args.id)
            print(f"reminder #{args.id} done")
            return 0
    return 0


def cmd_status(args) -> int:
    with get_tracker(args) as tr:
        prof = tr.get_profile()
        stats = tr.stats()
        print("== PROFILE ==")
        print(f"  name: {prof.get('name') or '(unset)'}")
        skills = prof.get("skills", [])
        print(f"  skills: {', '.join((s.get('name') if isinstance(s, dict) else str(s)) for s in skills) or '(none)'}")
        prefs = prof.get("work_preferences", {})
        print(f"  target roles: {', '.join(prefs.get('roles', [])) or '(none)'} | remote: {prefs.get('remote') or '?'}")
        print("== TARGETS ==")
        for t in tr.list_targets():
            score = stats["match_scores"].get(t["id"])
            print(f"  #{t['id']} {t['title']} @ {t['company']}" + (f"  match={score}/100" if score is not None else "  (not analyzed)"))
        print("== APPLICATIONS ==")
        apps = tr.list_applications()
        if not apps:
            print("  none yet")
        for status, count in stats["applications_by_status"].items():
            print(f"  {status}: {count}")
        for a in apps:
            title = a.get("target_title") or a["role_title"]
            print(f"  #{a['id']} [{a['status']}] {title} @ {a['company']}" + (f" follow-up {a['next_followup']}" if a["next_followup"] else ""))
        print("== REMINDERS ==")
        due = tr.due_reminders()
        print(f"  due/overdue: {len(due)}")
        for r in due:
            print(f"  #{r['id']} due {r['due_date']}: {r['message']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
