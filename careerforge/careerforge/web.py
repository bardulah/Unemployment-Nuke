"""Local web dashboard (stdlib http.server only).

Binds to 127.0.0.1 by default — the dashboard is a local tool, not a public
service. All stored text is HTML-escaped before rendering.
"""

from __future__ import annotations

import html
import json
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

from careerforge.db import APPLICATION_STATUSES, Tracker, today

CSS = """
:root { --bg:#0f1115; --card:#171a21; --fg:#e6e8ee; --muted:#9aa3b2; --accent:#7c5cff; --ok:#3fb27f; --warn:#e0a13c; --bad:#e05c5c; }
* { box-sizing: border-box; }
body { margin:0; font-family: ui-sans-serif, system-ui, "Segoe UI", Roboto, sans-serif; background:var(--bg); color:var(--fg); }
header { padding:14px 22px; border-bottom:1px solid #262b36; display:flex; gap:18px; align-items:baseline; position:sticky; top:0; background:var(--bg); }
header b { color:var(--accent); font-size:18px; }
nav a { color:var(--muted); text-decoration:none; margin-right:14px; font-size:14px; }
nav a:hover { color:var(--fg); }
main { padding:20px 22px; max-width:1100px; margin:0 auto; }
.card { background:var(--card); border:1px solid #262b36; border-radius:10px; padding:16px 18px; margin-bottom:16px; }
h2 { margin:0 0 10px; font-size:16px; color:var(--accent); }
h3 { margin:14px 0 6px; font-size:14px; }
table { border-collapse:collapse; width:100%; font-size:14px; }
th, td { text-align:left; padding:6px 10px; border-bottom:1px solid #262b36; vertical-align:top; }
th { color:var(--muted); font-weight:600; font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
a { color:#a99bff; }
.muted { color:var(--muted); }
.pill { display:inline-block; padding:2px 9px; border-radius:999px; font-size:12px; background:#232837; border:1px solid #333b4d; }
.pill.offer { background:#173527; border-color:#2c5c44; color:#7fe0ae; }
.pill.rejected, .pill.withdrawn { background:#3a1f1f; border-color:#5c2c2c; color:#f0a3a3; }
.pill.interview, .pill.screening { background:#33270f; border-color:#5c4a1f; color:#f0cd8a; }
.score { font-weight:700; }
form.inline { display:inline; }
input, select, textarea { background:#0f1218; color:var(--fg); border:1px solid #333b4d; border-radius:6px; padding:6px 8px; font-size:13px; }
button { background:var(--accent); color:#fff; border:0; border-radius:6px; padding:6px 12px; font-size:13px; cursor:pointer; }
button.ghost { background:transparent; border:1px solid #333b4d; color:var(--muted); }
pre.block { background:#0f1218; border:1px solid #262b36; border-radius:8px; padding:12px 14px; overflow-x:auto; font-size:13px; white-space:pre-wrap; }
.day { border-left:3px solid var(--accent); padding:4px 0 4px 12px; margin:8px 0; }
.tag { font-size:11px; color:var(--muted); border:1px solid #333b4d; border-radius:4px; padding:1px 6px; margin-left:6px; }
footer { color:var(--muted); font-size:12px; padding:18px 22px; }
"""


def esc(value) -> str:
    return html.escape("" if value is None else str(value))


def md(text: str) -> str:
    """Tiny markdown-ish renderer: headings, bullets, bold, code blocks."""
    text = esc(text)
    out = []
    in_pre = False
    for line in text.splitlines():
        if line.strip().startswith("```"):
            in_pre = not in_pre
            out.append("</pre>" if in_pre is False else "<pre class='block'>")
            continue
        if in_pre:
            out.append(line)
            continue
        stripped = line.strip()
        if stripped.startswith("### "):
            out.append(f"<h3>{stripped[4:]}</h3>")
        elif stripped.startswith("## "):
            out.append(f"<h2>{stripped[3:]}</h2>")
        elif stripped.startswith("# "):
            out.append(f"<h2>{stripped[2:]}</h2>")
        elif stripped.startswith("- "):
            out.append(f"<div style='margin-left:14px'>• {stripped[2:]}</div>")
        elif stripped:
            out.append(f"<div>{stripped}</div>")
    html_out = "\n".join(out).replace("<pre class='block'>", "<pre class='block'>")
    html_out = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", html_out)
    return html_out


def page(title: str, body: str) -> bytes:
    doc = f"""<!doctype html><html><head><meta charset='utf-8'>
<meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{esc(title)} — careerforge</title><style>{CSS}</style></head>
<body><header><b>careerforge</b><nav>
<a href='/'>Overview</a><a href='/targets'>Targets</a><a href='/tracker'>Tracker</a><a href='/api/stats'>API</a>
</nav></header><main>{body}</main>
<footer>Local dashboard · data stays in {esc("SQLite")} · Mistral key is read from env, never stored.</footer>
</body></html>"""
    return doc.encode("utf-8")


def score_pill(score) -> str:
    if score is None:
        return "<span class='muted'>n/a</span>"
    color = "var(--ok)" if score >= 70 else "var(--warn)" if score >= 45 else "var(--bad)"
    return f"<span class='score' style='color:{color}'>{score}/100</span>"


def overview_body(tr: Tracker) -> str:
    prof = tr.get_profile()
    stats = tr.stats()
    skills = prof.get("skills", [])
    skills_s = ", ".join((s.get("name") if isinstance(s, dict) else str(s)) for s in skills) or "—"
    prefs = prof.get("work_preferences", {})
    roles = ", ".join(prefs.get("roles", [])) or "—"
    parts = [
        "<div class='card'><h2>Master profile</h2>",
        f"<div><b>{esc(prof.get('name') or '(name unset)')}</b> "
        f"<span class='muted'>{esc(prof.get('contact', {}).get('email', ''))}</span></div>",
        f"<div class='muted'>skills: {esc(skills_s)}</div>",
        f"<div class='muted'>target roles: {esc(roles)} · remote: {esc(prefs.get('remote') or '?')} · locations: {esc(', '.join(prefs.get('locations', [])) or '?')}</div>",
        f"<div class='muted'>non-traditional background: {esc(prof.get('non_traditional_background') or '—')}</div>",
        "</div>",
        "<div class='card'><h2>Targets</h2><table><tr><th>#</th><th>Role</th><th>Company</th><th>Match</th><th></th></tr>",
    ]
    for t in tr.list_targets():
        score = stats["match_scores"].get(t["id"])
        parts.append(
            f"<tr><td>{t['id']}</td><td><a href='/targets/{t['id']}'>{esc(t['title'])}</a></td>"
            f"<td>{esc(t['company'])}</td><td>{score_pill(score)}</td><td class='muted'>{esc(t['location'])}</td></tr>"
        )
    parts.append("</table></div>")
    parts.append("<div class='card'><h2>Pipeline</h2><div>")
    for status in APPLICATION_STATUSES:
        count = stats["applications_by_status"].get(status, 0)
        if count:
            parts.append(f"<span class='pill {esc(status)}'>{esc(status)}: {count}</span> ")
    parts.append(f"<span class='pill' style='margin-left:8px'>overdue reminders: {stats['overdue_reminders']}</span>")
    parts.append("</div></div>")
    due = tr.due_reminders()
    if due:
        parts.append("<div class='card'><h2>Due / overdue reminders</h2>")
        for r in due:
            parts.append(f"<div>☐ #{r['id']} <b>{esc(r['due_date'])}</b> — {esc(r['message'])}</div>")
        parts.append("</div>")
    return "".join(parts)


def targets_body(tr: Tracker) -> str:
    stats = tr.stats()
    parts = ["<div class='card'><h2>Targets</h2><table><tr><th>#</th><th>Role</th><th>Company</th><th>Location</th><th>Match</th><th>JD</th></tr>"]
    for t in tr.list_targets():
        score = stats["match_scores"].get(t["id"])
        parts.append(
            f"<tr><td>{t['id']}</td><td><a href='/targets/{t['id']}'>{esc(t['title'])}</a></td><td>{esc(t['company'])}</td>"
            f"<td class='muted'>{esc(t['location'])}</td><td>{score_pill(score)}</td><td class='muted'>{len(t['jd_text'])} chars</td></tr>"
        )
    parts.append("</table><p class='muted'>Add targets from the CLI: <code>careerforge target add --title … --jd-file jd.txt --url https://…</code></p></div>")
    return "".join(parts)


def target_detail_body(tr: Tracker, target_id: int) -> str:
    t = tr.get_target(target_id)
    if not t:
        return "<div class='card'>target not found</div>"
    parts = [
        f"<div class='card'><h2>#{t['id']} {esc(t['title'])} @ {esc(t['company'])}</h2>",
        f"<div class='muted'>{esc(t['location'])} · {esc(t['url'])}</div>",
    ]
    if t.get("notes"):
        parts.append(f"<div class='muted'>notes: {esc(t['notes'])}</div>")
    parts.append("</div>")
    if t.get("jd_text"):
        parts.append(f"<div class='card'><h2>Job description</h2><pre class='block'>{esc(t['jd_text'][:6000])}</pre></div>")
    gap = tr.get_latest_result(target_id, "gap")
    if gap:
        p = gap["payload"]
        rows = "".join(
            f"<tr><td>{esc(s.get('skill'))}</td><td>{esc(s.get('current_level'))}</td><td>{esc(s.get('how_to_close'))}</td></tr>"
            for s in p.get("missing_skills", [])
        )
        proof = "".join(f"<div>• <b>{esc(x.get('proof'))}</b> — {esc(x.get('how_to_build'))}</div>" for x in p.get("missing_portfolio_proof", []))
        strengths = "".join(
            f"<div>• <b>{esc(s.get('strength'))}</b> <span class='muted'>[{esc(s.get('evidence'))}]</span> → {esc(s.get('framing'))}</div>"
            for s in p.get("transferable_strengths", [])
        )
        flags = "".join(f"<div>• {esc(r)}</div>" for r in p.get("red_flags", []))
        wins = "".join(f"<div>• {esc(q.get('action'))} <span class='muted'>(~{q.get('effort_days')}d)</span></div>" for q in p.get("quick_wins", []))
        parts.append(
            f"<div class='card'><h2>Gap analysis <span class='tag'>{esc(gap['mode'])} · {esc(gap['model'])}</span></h2>"
            f"<div>{score_pill(p.get('match_score'))} <b>{esc(p.get('one_line_verdict', ''))}</b></div>"
            f"<h3>Missing skills</h3><table><tr><th>Skill</th><th>Now</th><th>How to close</th></tr>{rows}</table>"
            f"<h3>Missing portfolio proof</h3>{proof}"
            f"<h3>Transferable strengths</h3>{strengths}"
            + (f"<h3>Red flags</h3>{flags}" if flags else "")
            + (f"<h3>Quick wins</h3>{wins}" if wins else "")
            + f"<h3>Brutal summary</h3><div>{md(p.get('brutal_summary', ''))}</div></div>"
        )
    proj = tr.get_latest_result(target_id, "project")
    if proj:
        p = proj["payload"]
        days = "".join(
            f"<div class='day'><b>Day {d.get('day')}</b> — {esc(d.get('focus'))}<br>"
            + "".join(f"<span class='muted'>• {esc(task)}</span><br>" for task in d.get("tasks", []))
            + f"<i>→ {esc(d.get('deliverable'))}</i></div>"
            for d in p.get("days", [])
        )
        parts.append(
            f"<div class='card'><h2>14-day micro-project <span class='tag'>{esc(proj['mode'])} · {esc(proj['model'])}</span></h2>"
            f"<div><b>{esc(p.get('title'))}</b></div>"
            f"<div class='muted'>{esc(p.get('company_problem'))}</div>"
            f"<div class='muted'>Stack: {esc(', '.join(p.get('stack', [])))}</div>"
            f"{days}"
            f"<h3>Deliverables</h3>{''.join(f'<div>• {esc(x)}</div>' for x in p.get('final_deliverables', []))}"
            f"<h3>Demo script</h3>{''.join(f'<div>• {esc(x)}</div>' for x in p.get('demo_script', []))}"
            f"<h3>Success metrics</h3>{''.join(f'<div>• {esc(x)}</div>' for x in p.get('success_metrics', []))}"
            "</div>"
        )
    tail = tr.get_latest_result(target_id, "tailor")
    if tail:
        p = tail["payload"]
        bullets = ""
        for section in p.get("cv_bullets", []):
            bullets += f"<h3>{esc(section.get('section'))}</h3>" + "".join(f"<div>• {esc(b)}</div>" for b in section.get("bullets", []))
        out = p.get("outreach", {})
        parts.append(
            f"<div class='card'><h2>Tailored CV + outreach <span class='tag'>{esc(tail['mode'])} · {esc(tail['model'])}</span></h2>"
            f"<h3>CV summary</h3><div>{md(p.get('cv_summary', ''))}</div>"
            f"{bullets}"
            + (f"<h3>Skills section</h3><div>{esc(', '.join(p.get('skills_section', [])))}</div>" if p.get("skills_section") else "")
            + f"<h3>Outreach</h3><div><b>Subject:</b> {esc(out.get('subject', ''))}</div>"
            f"<pre class='block'>{esc(out.get('email_body', ''))}</pre>"
            f"<div><b>LinkedIn DM:</b></div><pre class='block'>{esc(out.get('linkedin_dm', ''))}</pre>"
            + (f"<h3>Tips</h3>{''.join(f'<div>• {esc(t)}</div>' for t in out.get('tips', []))}" if out.get("tips") else "")
            + "</div>"
        )
    if not (gap or proj or tail):
        parts.append("<div class='card muted'>Nothing generated yet. Run: <code>careerforge run " + str(target_id) + "</code></div>")
    return "".join(parts)


def tracker_body(tr: Tracker) -> str:
    apps = tr.list_applications()
    rems = tr.list_reminders(include_done=False)
    status_options = "".join(f"<option value='{s}'>{s}</option>" for s in APPLICATION_STATUSES)
    rows = []
    for a in apps:
        title = a.get("target_title") or a["role_title"]
        options = "".join(
            f"<option value='{s}'{' selected' if s == a['status'] else ''}>{s}</option>" for s in APPLICATION_STATUSES
        )
        rows.append(
            f"<tr><td>#{a['id']}</td><td>{esc(title)}</td><td>{esc(a['company'])}</td>"
            f"<td><form class='inline' method='post' action='/api/applications/{a['id']}/set'>"
            f"<select name='status'>{options}</select> "
            f"<input name='followup' placeholder='follow-up YYYY-MM-DD' value='{esc(a['next_followup'])}' size='12'> "
            f"<input name='note' placeholder='note' value='{esc(a['notes'])}' size='18'> "
            f"<button class='ghost' type='submit'>save</button></form></td>"
            f"<td class='muted'>{esc(a['contact'])}</td></tr>"
        )
    parts = [
        "<div class='card'><h2>Applications</h2>",
        "<table><tr><th>#</th><th>Role</th><th>Company</th><th>Status / follow-up / note</th><th>Contact</th></tr>",
        *rows,
        "</table>",
        "<form method='post' action='/api/applications/add' style='margin-top:10px'>"
        "<input name='title' placeholder='role title' required> <input name='company' placeholder='company'> "
        f"<select name='status'>{status_options}</select> <input name='contact' placeholder='contact'> "
        "<input name='followup' placeholder='follow-up YYYY-MM-DD' size='12'> <input name='note' placeholder='note'> "
        "<button type='submit'>add application</button></form></div>",
        "<div class='card'><h2>Reminders</h2>",
    ]
    for r in rems:
        parts.append(
            f"<div>☐ #{r['id']} <b>{esc(r['due_date'])}</b> — {esc(r['message'])} "
            f"<form class='inline' method='post' action='/api/reminders/{r['id']}/done'><button class='ghost' type='submit'>done</button></form></div>"
        )
    parts.append(
        "<form method='post' action='/api/reminders/add' style='margin-top:10px'>"
        "<input name='message' placeholder='follow up with recruiter…' required size='40'> "
        "<input name='due' placeholder='YYYY-MM-DD' required size='12'> "
        "<button type='submit'>add reminder</button></form></div>"
    )
    return "".join(parts)


def make_handler(data_dir: str):
    class Handler(BaseHTTPRequestHandler):
        server_version = "careerforge/0.1"

        def log_message(self, fmt, *a):  # quiet
            pass

        def _send(self, body: bytes, status: int = 200, content_type: str = "text/html; charset=utf-8"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _json(self, obj, status: int = 200):
            self._send(json.dumps(obj, ensure_ascii=False, indent=2).encode("utf-8"), status, "application/json; charset=utf-8")

        def _redirect(self, location: str):
            self.send_response(303)
            self.send_header("Location", location)
            self.send_header("Content-Length", "0")
            self.end_headers()

        def do_GET(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/") or "/"
            with Tracker(data_dir) as tr:
                if path == "/":
                    self._send(page("Overview", overview_body(tr)))
                elif path == "/targets":
                    self._send(page("Targets", targets_body(tr)))
                elif path.startswith("/targets/"):
                    try:
                        tid = int(path.split("/")[-1])
                    except ValueError:
                        self._send(page("404", "<div class='card'>bad id</div>"), 404)
                        return
                    self._send(page(f"Target {tid}", target_detail_body(tr, tid)))
                elif path == "/tracker":
                    self._send(page("Tracker", tracker_body(tr)))
                elif path == "/api/stats":
                    self._json(tr.stats())
                elif path == "/api/profile":
                    self._json(tr.get_profile())
                elif path == "/api/targets":
                    targets = tr.list_targets()
                    for t in targets:
                        t["latest"] = {
                            kind: tr.get_latest_result(t["id"], kind) for kind in ("gap", "project", "tailor")
                        }
                    self._json(targets)
                elif path == "/api/applications":
                    self._json(tr.list_applications())
                elif path == "/api/reminders":
                    self._json(tr.list_reminders(include_done=True))
                else:
                    self._send(page("404", "<div class='card'>not found</div>"), 404)

        def do_POST(self):
            parsed = urlparse(self.path)
            path = parsed.path.rstrip("/")
            length = int(self.headers.get("Content-Length") or 0)
            form = parse_qs(self.rfile.read(length).decode("utf-8", errors="replace")) if length else {}
            flat = {k: v[0] for k, v in form.items()}
            with Tracker(data_dir) as tr:
                if path == "/api/applications/add":
                    app_id = tr.add_application(
                        status=flat.get("status", "saved"), role_title=flat.get("title", ""),
                        company=flat.get("company", ""), contact=flat.get("contact", ""),
                        next_followup=flat.get("followup", ""), notes=flat.get("note", ""),
                    )
                    self._json({"id": app_id})
                elif path.startswith("/api/applications/") and path.endswith("/set"):
                    app_id = int(path.split("/")[3])
                    tr.update_application(app_id, status=flat.get("status"), next_followup=flat.get("followup"),
                                          notes=flat.get("note"), contact=flat.get("contact"))
                    self._redirect("/tracker")
                elif path == "/api/reminders/add":
                    rid = tr.add_reminder(flat.get("message", ""), flat.get("due", today()))
                    self._redirect("/tracker")
                    return
                elif path.startswith("/api/reminders/") and path.endswith("/done"):
                    tr.complete_reminder(int(path.split("/")[3]))
                    self._redirect("/tracker")
                    return
                else:
                    self._send(page("404", "<div class='card'>not found</div>"), 404)

    return Handler


def make_server(data_dir: str, host: str = "127.0.0.1", port: int = 8000) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost", "::1"):
        raise ValueError("the dashboard binds to loopback only (127.0.0.1/localhost) — refusing a non-loopback host")
    return ThreadingHTTPServer((host, port), make_handler(data_dir))


def serve(data_dir: str, host: str = "127.0.0.1", port: int = 8000) -> None:
    server = make_server(data_dir, host, port)
    actual_host, actual_port = server.server_address[:2]
    print(f"careerforge dashboard: http://{actual_host}:{actual_port}  (Ctrl+C to stop)")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
