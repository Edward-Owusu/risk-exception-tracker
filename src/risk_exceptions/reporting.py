"""Reports: HTML, Markdown, CSV, JSON, an expiry timeline (SVG) and risk acceptance memos."""

from __future__ import annotations

import csv
import io
import json
from datetime import date, timedelta
from html import escape

from . import __version__
from .engine import LANES, SEV_ORDER, ExceptionResult, Report

LANE_COLORS = {
    "Expired, still open": "#B42318",
    "Expiring soon": "#C27803",
    "Active": "#1F6F5C",
    "Pending approval": "#5B6B7F",
    "Closed": "#9AA4B2",
}
SEV_COLORS = {"critical": "#B42318", "high": "#C2410C", "medium": "#A16207", "low": "#4B5563"}


def _d(v: date | None) -> str:
    return v.isoformat() if v else ""


def _refs(f) -> str:
    return "; ".join(x for x in ("NIST " + ", ".join(f.nist) if f.nist else "",
                                 "ISO 27001 " + ", ".join(f.iso) if f.iso else "",
                                 "CSF " + ", ".join(f.csf) if f.csf else "") if x)


# ---------------------------------------------------------------- timeline

def timeline_svg(report: Report, include_closed: bool = False, width: int = 960) -> str:
    """A bar per exception from approval to expiry, with a line for the as-of date."""
    rows = [r for r in report.results if include_closed or r.exception.status != "closed"]
    if not rows:
        return "<p>No open exceptions to show.</p>"
    rows = sorted(rows, key=lambda r: (r.exception.expiry_date or date.max, r.exception.exception_id))
    as_of = report.as_of
    starts = [r.exception.approved_date for r in rows if r.exception.approved_date]
    ends = [r.exception.expiry_date for r in rows if r.exception.expiry_date]
    lo = min(starts + ends + [as_of]) - timedelta(days=15)
    hi = max(ends + [as_of + timedelta(days=report.model["expiring_soon_days"])]) + timedelta(days=30)
    lo = lo.replace(day=1)
    label_w, top, row_h, right = 250, 40, 26, 44
    plot_w = width - label_w - right
    height = top + row_h * len(rows) + 12
    span = max((hi - lo).days, 1)

    def x(d: date) -> float:
        return label_w + plot_w * (d - lo).days / span

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="100%" role="img" '
           f'aria-label="Exception expiry timeline" font-family="Inter, Segoe UI, Arial, sans-serif" font-size="12">',
           '<style>.halo{paint-order:stroke;stroke:#fff;stroke-width:4px;stroke-linejoin:round}</style>']
    # month grid
    xa = x(as_of)
    m = lo
    while m <= hi:
        xm = x(m)
        out.append(f'<line x1="{xm:.1f}" y1="{top - 4}" x2="{xm:.1f}" y2="{height - 8}" stroke="#E4E7EC" />')
        if (m.month in (1, 4, 7, 10) or span < 400) and abs(xm + 25 - xa) > 40:
            out.append(f'<text x="{xm + 3:.1f}" y="{top - 8}" fill="#667085">{m.strftime("%b %Y")}</text>')
        m = (m.replace(day=28) + timedelta(days=4)).replace(day=1)
    notes = []  # text on the plot area, drawn last so the as-of line passes behind it
    for i, r in enumerate(rows):
        e = r.exception
        y = top + i * row_h
        color = LANE_COLORS[r.lane]
        label = f"{e.exception_id}  {e.title}"
        if len(label) > 31:
            label = label[:30] + "…"
        out.append(f'<text x="8" y="{y + 16}" fill="#101828"><title>{escape(e.title)}</title>{escape(label)}</text>')
        start = e.approved_date or lo
        if e.status == "pending" and not e.approved_date:
            notes.append(f'<text class="halo" x="{label_w + 6}" y="{y + 17}" fill="{color}" font-style="italic">awaiting approval</text>')
        elif not e.approved_date and e.expiry_date:
            xe = x(e.expiry_date)
            out.append(f'<path d="M{xe:.1f} {y + 5} l7 8 l-7 8 l-7 -8 z" fill="{color}"><title>{escape(e.exception_id)}: '
                       f'expires {_d(e.expiry_date)}, never approved</title></path>')
            notes.append(f'<text class="halo" x="{xe - 12:.1f}" y="{y + 17}" text-anchor="end" fill="{color}" font-style="italic">'
                       f'no approval recorded</text>')
        elif e.expiry_date:
            x1, x2 = x(start), x(e.expiry_date)
            out.append(f'<rect x="{x1:.1f}" y="{y + 6}" width="{max(x2 - x1, 3):.1f}" height="14" rx="3" fill="{color}" '
                       f'opacity="{0.55 if e.status == "closed" else 0.9}"><title>{escape(e.exception_id)}: '
                       f'{_d(e.approved_date) or "no approval date"} to {_d(e.expiry_date)} ({escape(r.lane)})</title></rect>')
        else:
            x1 = x(start)
            out.append(f'<rect x="{x1:.1f}" y="{y + 6}" width="{label_w + plot_w - x1:.1f}" height="14" rx="3" '
                       f'fill="none" stroke="{color}" stroke-width="2" stroke-dasharray="5 3"><title>{escape(e.exception_id)}: '
                       f'no expiry date</title></rect>')
            notes.append(f'<text class="halo" x="{label_w + plot_w - 4:.1f}" y="{y + 17}" text-anchor="end" fill="{color}">no expiry</text>')
        if r.findings:
            out.append(f'<circle cx="{label_w - 12}" cy="{y + 13}" r="5" fill="{SEV_COLORS[r.worst]}">'
                       f'<title>{len(r.findings)} finding(s), worst {r.worst}</title></circle>')
    out.append(f'<line x1="{xa:.1f}" y1="{top - 22}" x2="{xa:.1f}" y2="{height - 6}" stroke="#101828" stroke-width="2" />')
    out.append(f'<text x="{xa:.1f}" y="{top - 26}" text-anchor="middle" fill="#101828" font-weight="600">as of {as_of.isoformat()}</text>')
    out.extend(notes)
    out.append("</svg>")
    return "".join(out)


# ---------------------------------------------------------------- HTML

CSS = """
:root { --ink:#101828; --muted:#667085; --line:#E4E7EC; --paper:#FBFAF7; --card:#FFFFFF; --accent:#1F6F5C; }
* { box-sizing: border-box; }
body { margin:0; font-family: Inter, "Segoe UI", Arial, sans-serif; color:var(--ink); background:var(--paper); line-height:1.5; }
header { background:#0F2A24; color:#F4F1EA; padding:32px 40px 26px; }
header h1 { margin:0 0 4px; font-size:28px; font-weight:650; letter-spacing:-0.01em; }
header p { margin:0; color:#B9C7C1; }
main { max-width:1100px; margin:0 auto; padding:28px 40px 60px; }
h2 { font-size:19px; margin:36px 0 10px; }
.kpis { display:grid; grid-template-columns:repeat(4, minmax(0,1fr)); gap:14px; margin-top:-46px; }
.kpi { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px 16px; }
.kpi b { display:block; font-size:26px; }
.kpi span { color:var(--muted); font-size:13px; }
table { width:100%; border-collapse:collapse; background:var(--card); font-size:13.5px; }
th, td { text-align:left; padding:8px 10px; border-bottom:1px solid var(--line); vertical-align:top; }
th { background:#F2F4F7; font-weight:600; }
.pill { display:inline-block; padding:1px 8px; border-radius:999px; color:#fff; font-size:12px; font-weight:600; text-transform:capitalize; }
.lanes { display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:10px; }
.lane { background:var(--card); border:1px solid var(--line); border-top:4px solid; border-radius:8px; padding:10px 12px; }
.lane b { font-size:22px; display:block; }
.lane span { font-size:12.5px; color:var(--muted); }
.box { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:14px; }
.note { color:var(--muted); font-size:13px; }
code { background:#F2F4F7; padding:1px 4px; border-radius:4px; }
footer { color:var(--muted); font-size:12.5px; margin-top:40px; }
@media (max-width: 760px) { .kpis, .lanes { grid-template-columns:repeat(2, minmax(0,1fr)); } main, header { padding-left:16px; padding-right:16px; } }
"""


def _pill(sev: str) -> str:
    return f'<span class="pill" style="background:{SEV_COLORS[sev]}">{escape(sev)}</span>'


def to_html(report: Report) -> str:
    h, c = report.health(), report.counts()
    m = report.model
    lanes = "".join(f'<div class="lane" style="border-top-color:{LANE_COLORS[l]}"><b>{c["lanes"][l]}</b><span>{escape(l)}</span></div>'
                    for l in LANES)
    risk_rows = "".join(f"<tr><td style='text-transform:capitalize'>{escape(k)}</td><td>{v}</td></tr>"
                        for k, v in c["by_risk"].items() if v or k != "unrated")
    owner_rows = "".join(f"<tr><td>{escape(o['owner'])}</td><td>{o['exceptions']}</td><td>{o['risk_load']}</td>"
                         f"<td>{o['expired']}</td><td>{o['findings']}</td></tr>" for o in report.by_owner())
    find_rows = "".join(
        f"<tr><td>{_pill(f.severity)}</td><td><b>{escape(f.exception_id)}</b><br><span class='note'>{escape(f.exception_title)}</span></td>"
        f"<td><b>{escape(f.rule_id)}</b> {escape(f.title)}<br>{escape(f.detail)}</td><td>{escape(f.fix)}</td>"
        f"<td class='note'>{escape(_refs(f))}</td></tr>" for f in report.findings) or \
        "<tr><td colspan='5'>No findings. Every active exception is well governed.</td></tr>"
    reg_rows = "".join(
        f"<tr><td><b>{escape(r.exception.exception_id)}</b></td><td>{escape(r.exception.title)}</td>"
        f"<td style='text-transform:capitalize'>{escape(r.exception.risk_level or 'unrated')}</td><td>{escape(r.exception.risk_owner)}</td>"
        f"<td>{_d(r.exception.expiry_date) or '<i>none</i>'}</td>"
        f"<td><span style='color:{LANE_COLORS[r.lane]};font-weight:600'>{escape(r.lane)}</span></td>"
        f"<td>{escape(r.governance)}</td></tr>" for r in report.results)
    na = [f"{r.exception.exception_id}: {n}" for r in report.results for n in r.not_assessed]
    na_html = ("<h2>Not assessed</h2><ul>" + "".join(f"<li>{escape(n)}</li>" for n in na) + "</ul>") if na else ""
    roster_note = ("A people roster was used to confirm approver authority and who has left."
                   if report.roster_used else
                   "No people roster was supplied, so approver authority comes from the approver role column and "
                   "departed staff could not be checked (RE-08 and part of RE-07).")
    sev_counts = " · ".join(f"{c['findings'][s]} {s}" for s in SEV_ORDER)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Risk exception review: {escape(report.organization)}</title><style>{CSS}</style></head><body>
<header><h1>Risk exception review</h1><p>{escape(report.organization)} · as of {report.as_of.isoformat()} · {c['total']} exceptions in the register</p></header>
<main>
<div class="kpis">
<div class="kpi"><b>{h['score']:.0f}</b><span>Governance health ({escape(h['label'])})</span></div>
<div class="kpi"><b>{c['active']}</b><span>Active exceptions</span></div>
<div class="kpi"><b>{c['lanes']['Expired, still open']}</b><span>Expired but still open</span></div>
<div class="kpi"><b>{c['accepted_risk_load']}</b><span>Accepted risk load (weighted)</span></div>
</div>
<h2>Where every exception stands</h2><div class="lanes">{lanes}</div>
<h2>Expiry timeline</h2><div class="box">{timeline_svg(report)}</div>
<p class="note">Bars run from approval to expiry. Red bars have expired, amber bars expire within {m['expiring_soon_days']} days, and dashed bars have no expiry date. A dot beside the name shows the most severe finding.</p>
<h2>Findings ({len(report.findings)})</h2><p class="note">{sev_counts}</p>
<table><tr><th>Severity</th><th>Exception</th><th>Finding</th><th>Fix</th><th>References</th></tr>{find_rows}</table>
<h2>Accepted risk by level</h2><table style="max-width:420px"><tr><th>Risk level</th><th>Active exceptions</th></tr>{risk_rows}</table>
<h2>Risk owners</h2><table><tr><th>Risk owner</th><th>Active exceptions</th><th>Risk load</th><th>Expired</th><th>Findings</th></tr>{owner_rows}</table>
<h2>Register</h2><table><tr><th>ID</th><th>Exception</th><th>Risk</th><th>Owner</th><th>Expires</th><th>Status</th><th>Governance</th></tr>{reg_rows}</table>
{na_html}
<h2>How the health score works</h2>
<p>Each active exception is weighted by its risk level (critical {m['weights']['critical']}, high {m['weights']['high']}, medium {m['weights']['medium']}, low {m['weights']['low']}; unrated counts as high). An exception counts in full if its worst finding is low or there is none, half if its worst finding is medium, and not at all if it has a high or critical finding. The score is the governed share of the total weight: {h['governed_weight']:g} of {h['total_weight']}. Bands: {', '.join(f"{b['min']}+ {b['label']}" for b in m['health_bands'])}.</p>
<p class="note">{escape(roster_note)}</p>
<footer>Generated by risk-exception-tracker {__version__}. The tool checks how exceptions are governed from the register supplied; it does not judge whether accepting each risk was the right business decision.</footer>
</main></body></html>"""


# ---------------------------------------------------------------- Markdown, CSV, JSON

def to_markdown(report: Report) -> str:
    h, c = report.health(), report.counts()
    lines = [f"# Risk exception review: {report.organization}", "",
             f"As of {report.as_of.isoformat()}. {c['total']} exceptions in the register, {c['active']} active.", "",
             f"**Governance health: {h['score']:.0f}/100 ({h['label']})**. Accepted risk load: {c['accepted_risk_load']}.", "",
             "| Status | Count |", "|---|---|"]
    lines += [f"| {l} | {c['lanes'][l]} |" for l in LANES]
    lines += ["", f"## Findings ({len(report.findings)})", ""]
    if report.findings:
        lines += ["| Severity | Exception | Finding | Fix | References |", "|---|---|---|---|---|"]
        for f in report.findings:
            lines.append(f"| {f.severity} | {f.exception_id} {f.exception_title} | {f.rule_id} {f.title}: {f.detail} | {f.fix} | {_refs(f)} |")
    else:
        lines.append("No findings. Every active exception is well governed.")
    lines += ["", "## Risk owners", "", "| Risk owner | Active | Risk load | Expired | Findings |", "|---|---|---|---|---|"]
    lines += [f"| {o['owner']} | {o['exceptions']} | {o['risk_load']} | {o['expired']} | {o['findings']} |" for o in report.by_owner()]
    lines += ["", "## Register", "", "| ID | Exception | Risk | Owner | Expires | Status | Governance |", "|---|---|---|---|---|---|---|"]
    for r in report.results:
        e = r.exception
        lines.append(f"| {e.exception_id} | {e.title} | {e.risk_level or 'unrated'} | {e.risk_owner} | {_d(e.expiry_date) or 'none'} | {r.lane} | {r.governance} |")
    na = [f"- {r.exception.exception_id}: {n}" for r in report.results for n in r.not_assessed]
    if na:
        lines += ["", "## Not assessed", ""] + na
    lines += ["", f"_Generated by risk-exception-tracker {__version__}._", ""]
    return "\n".join(lines)


def to_csv(report: Report) -> str:
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["severity", "rule_id", "finding", "exception_id", "exception", "risk_level", "risk_owner",
                "expiry_date", "status", "detail", "fix", "nist_800_53", "iso_27001", "csf_2_0"])
    by_id = {r.exception.exception_id: r for r in report.results}
    for f in report.findings:
        r = by_id[f.exception_id]
        w.writerow([f.severity, f.rule_id, f.title, f.exception_id, f.exception_title, r.exception.risk_level or "",
                    r.exception.risk_owner, _d(r.exception.expiry_date), r.lane, f.detail, f.fix,
                    ", ".join(f.nist), ", ".join(f.iso), ", ".join(f.csf)])
    return buf.getvalue()


def to_json(report: Report) -> str:
    return json.dumps(report.to_dict(), indent=2)


WRITERS = {"html": to_html, "md": to_markdown, "csv": to_csv, "json": to_json}


# ---------------------------------------------------------------- risk acceptance memo

def acceptance_memo(result: ExceptionResult, organization: str, as_of: date, fmt: str = "md") -> str:
    """A one-page risk acceptance memo for an exception, ready for signature."""
    e = result.exception
    issues = result.findings
    facts = [
        ("Exception ID", e.exception_id), ("Title", e.title), ("Policy or standard", e.policy_or_standard),
        ("Control references", e.control_refs), ("Scope", e.scope), ("Risk level", (e.risk_level or "not rated").capitalize()),
        ("Requested by", e.requested_by), ("Risk owner", e.risk_owner), ("Approved by", e.approved_by),
        ("Approver role", e.approver_role), ("Approved on", _d(e.approved_date)), ("Expires on", _d(e.expiry_date) or "No expiry date set"),
        ("Compensating control", e.compensating_control or "None recorded"),
        ("Control last verified", _d(e.control_verified_date) or "Not recorded"),
        ("Remediation plan", e.remediation_plan or "None recorded"), ("Remediation due", _d(e.remediation_due)),
        ("Times renewed", str(e.renewal_count)),
    ]
    statement = (f"I have reviewed the risk described above. I understand that {organization} is operating outside "
                 f"{e.policy_or_standard or 'its policy'} for the scope listed, and I accept the residual risk until "
                 f"{_d(e.expiry_date) or '[expiry date]'}, subject to the compensating control and remediation plan recorded here.")
    if fmt == "md":
        out = [f"# Risk acceptance memo: {e.exception_id}", "", f"{organization} · prepared {as_of.isoformat()}", "",
               "| Item | Detail |", "|---|---|"]
        out += [f"| {k} | {v} |" for k, v in facts if v]
        out += ["", "## Reason for the exception", "", e.reason or "Not recorded.", ""]
        if issues:
            out += ["## Open governance issues", "", "Resolve these before signing:", ""]
            out += [f"- **{f.rule_id} ({f.severity})** {f.title}: {f.detail}" for f in issues]
            out.append("")
        out += ["## Acceptance", "", statement, "",
                "Risk owner: ______________________  Date: __________", "",
                "Approver: ________________________  Date: __________", ""]
        return "\n".join(out)
    rows = "".join(f"<tr><th>{escape(k)}</th><td>{escape(v)}</td></tr>" for k, v in facts if v)
    iss = ""
    if issues:
        iss = "<h2>Open governance issues</h2><p>Resolve these before signing:</p><ul>" + "".join(
            f"<li><b>{escape(f.rule_id)} ({escape(f.severity)})</b> {escape(f.title)}: {escape(f.detail)}</li>" for f in issues) + "</ul>"
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Risk acceptance memo {escape(e.exception_id)}</title>
<style>body{{font-family:Georgia,'Times New Roman',serif;max-width:760px;margin:40px auto;padding:0 20px;color:#101828;line-height:1.55}}
h1{{font-size:24px;margin-bottom:2px}} .sub{{color:#667085;margin-top:0}} table{{border-collapse:collapse;width:100%;font-family:Arial,sans-serif;font-size:14px}}
th,td{{text-align:left;border-bottom:1px solid #E4E7EC;padding:7px 8px;vertical-align:top}} th{{width:34%;color:#475467;font-weight:600}}
.sign{{margin-top:36px;display:grid;grid-template-columns:1fr 1fr;gap:36px}} .sign div{{border-top:1px solid #101828;padding-top:6px;font-family:Arial,sans-serif;font-size:13px}}</style></head>
<body><h1>Risk acceptance memo: {escape(e.exception_id)}</h1><p class="sub">{escape(organization)} · prepared {as_of.isoformat()}</p>
<table>{rows}</table><h2>Reason for the exception</h2><p>{escape(e.reason or 'Not recorded.')}</p>{iss}
<h2>Acceptance</h2><p>{escape(statement)}</p>
<div class="sign"><div>Risk owner signature and date</div><div>Approver signature and date</div></div></body></html>"""
