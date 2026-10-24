"""Risk Exception Tracker: a working register for security policy exceptions and risk acceptances.

Run with:  streamlit run app/streamlit_app.py
"""

from __future__ import annotations

import sys
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from risk_exceptions import __version__  # noqa: E402
from risk_exceptions.engine import LANES, REGISTER_COLUMNS, SEV_ORDER, DataError, assess, load_model, parse_register, parse_roster  # noqa: E402
from risk_exceptions.reporting import LANE_COLORS, SEV_COLORS, WRITERS, acceptance_memo, timeline_svg  # noqa: E402
from risk_exceptions.table import register_rows, rows_to_csv, rows_to_register  # noqa: E402

SAMPLES = ROOT / "samples"
SOURCES = {
    "Riverbend Components": ("riverbend_components_exceptions.csv", "riverbend_components_people.csv"),
    "Northfield Cold Logistics": ("northfield_cold_logistics_exceptions.csv", "northfield_cold_logistics_people.csv"),
    "My own register": (None, None),
}
VIEWS = ["Overview", "Lifecycle board", "Expiry timeline", "Edit register", "Acceptance memo"]
SAMPLE_AS_OF = date(2026, 10, 24)

st.set_page_config(page_title="Risk Exception Tracker", page_icon="📒", layout="wide",
                   initial_sidebar_state="collapsed")

# ---------------------------------------------------------------- look and feel
st.markdown("""
<style>
[data-testid="stSidebar"], [data-testid="collapsedControl"] { display: none; }
.block-container { padding-top: 1.2rem; max-width: 1240px; }
.rx-band { background: #0F2A24; color: #F4F1EA; border-radius: 14px; padding: 22px 26px 18px; margin-bottom: 14px; }
.rx-band h1 { font-family: Georgia, 'Times New Roman', serif; font-size: 30px; font-weight: 600; margin: 0; color: #F4F1EA; padding: 0; }
.rx-band p { margin: 4px 0 0; color: #B9C7C1; font-size: 14.5px; }
.rx-tile { background: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 12px; padding: 14px 16px; height: 100%; }
.rx-tile b { font-size: 28px; display: block; line-height: 1.15; color: #101828; }
.rx-tile span { color: #667085; font-size: 13px; }
.rx-lanehead { border-top: 5px solid; border-radius: 10px 10px 0 0; background: #FFFFFF; border-left: 1px solid #E4E7EC;
  border-right: 1px solid #E4E7EC; padding: 8px 12px; font-weight: 650; font-size: 14px; color: #101828; }
.rx-card { background: #FFFFFF; border: 1px solid #E4E7EC; border-left: 4px solid; border-radius: 8px; padding: 10px 12px; margin: 8px 0; }
.rx-card .id { font-size: 12px; color: #667085; font-weight: 600; letter-spacing: .02em; }
.rx-card .t { font-size: 14px; font-weight: 600; color: #101828; margin: 2px 0 6px; line-height: 1.3; }
.rx-card .m { font-size: 12.5px; color: #475467; }
.rx-pill { display: inline-block; padding: 1px 8px; border-radius: 999px; color: #fff; font-size: 11.5px; font-weight: 650;
  text-transform: capitalize; margin-right: 4px; }
.rx-find { background: #FFFFFF; border: 1px solid #E4E7EC; border-radius: 10px; padding: 10px 14px; margin-bottom: 8px; }
.rx-find .h { font-weight: 600; color: #101828; }
.rx-find .d { color: #344054; font-size: 14px; margin: 3px 0; }
.rx-find .f { color: #1F6F5C; font-size: 13.5px; }
.rx-find .r { color: #667085; font-size: 12px; }
.rx-empty { color: #98A2B3; font-size: 13px; padding: 10px 4px; }
</style>
""", unsafe_allow_html=True)


def pill(text: str, color: str) -> str:
    return f'<span class="rx-pill" style="background:{color}">{escape(text)}</span>'


def gauge(score: float, label: str) -> str:
    """A half-circle gauge for the governance health score."""
    import math
    color = "#1F6F5C" if score >= 85 else "#C27803" if score >= 65 else "#C2410C" if score >= 40 else "#B42318"
    angle = math.pi * (1 - score / 100)
    x, y = 100 + 80 * math.cos(angle), 100 - 80 * math.sin(angle)
    large = 0
    return (f'<svg viewBox="0 0 200 122" width="100%" style="max-width:260px">'
            f'<path d="M20 100 A80 80 0 0 1 180 100" fill="none" stroke="#E4E7EC" stroke-width="16" stroke-linecap="round"/>'
            f'<path d="M20 100 A80 80 0 {large} 1 {x:.1f} {y:.1f}" fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round"/>'
            f'<text x="100" y="92" text-anchor="middle" font-size="34" font-weight="700" fill="#101828" '
            f'font-family="Georgia, serif">{score:.0f}</text>'
            f'<text x="100" y="116" text-anchor="middle" font-size="13" fill="{color}" font-weight="600" '
            f'font-family="Arial, sans-serif">{escape(label)}</text></svg>')


def tile(value, text: str) -> str:
    return f'<div class="rx-tile"><b>{escape(str(value))}</b><span>{escape(text)}</span></div>'


def choose(label: str, options: list[str], key: str, default: str | None = None) -> str:
    """Segmented buttons on Streamlit 1.40+, horizontal radio on older versions."""
    default = default or options[0]
    if hasattr(st, "segmented_control"):
        picked = st.segmented_control(label, options, default=default, key=key, label_visibility="collapsed")
        return picked or default
    return st.radio(label, options, index=options.index(default), key=key, horizontal=True, label_visibility="collapsed")


# ---------------------------------------------------------------- header and data source
st.markdown('<div class="rx-band"><h1>Risk Exception Tracker</h1>'
            '<p>Every policy exception and risk acceptance in one register, with the ones that are no longer governed '
            'flagged before an auditor finds them.</p></div>', unsafe_allow_html=True)

src_col, date_col, rules_col = st.columns([3.2, 1.4, 1])
with src_col:
    source = choose("Register", list(SOURCES), key="source")
with date_col:
    default_as_of = SAMPLE_AS_OF if source != "My own register" else date.today()
    as_of = st.date_input("Check as of", value=default_as_of, key=f"asof_{source}",
                          help="Expiry dates and verification ages are measured against this date. "
                               "The samples are set to 24 October 2026.")
with rules_col:
    with st.popover("Your rules", use_container_width=True):
        st.caption("Organization-defined limits. Changes apply straight away.")
        base = load_model()
        soon = st.number_input("Expiring soon window (days)", 1, 180, base["expiring_soon_days"])
        renewals = st.number_input("Maximum renewals", 0, 20, base["max_renewals"])
        verify = st.number_input("Verify compensating controls every (days)", 7, 730, base["control_verification_days"])
        st.markdown("**Longest approval allowed, by risk level (days)**")
        durations = {lvl: st.number_input(lvl.capitalize(), 7, 1095, base["max_duration_days"][lvl], key=f"dur_{lvl}")
                     for lvl in reversed(base["risk_levels"])}

model = load_model(overrides={"expiring_soon_days": soon, "max_renewals": renewals,
                              "control_verification_days": verify, "max_duration_days": durations})

# Load the chosen register into session state once per source, so edits survive reruns.
if st.session_state.get("loaded_source") != source:
    reg_file, roster_file = SOURCES[source]
    st.session_state["loaded_source"] = source
    st.session_state["roster_text"] = (SAMPLES / roster_file).read_text(encoding="utf-8") if roster_file else None
    st.session_state["rows"] = (register_rows(parse_register((SAMPLES / reg_file).read_text(encoding="utf-8"), model))
                                if reg_file else [])
    st.session_state["org"] = f"{source} (fictional)" if reg_file else "My organization"
    st.session_state["editor_version"] = st.session_state.get("editor_version", 0) + 1

if source == "My own register":
    with st.container(border=True):
        st.markdown("**Load your register.** Start from the template, or build it from scratch in **Edit register**. "
                    "Files are processed in memory and not saved.")
        u1, u2, u3 = st.columns([2, 2, 1.4])
        with u1:
            up = st.file_uploader("Exception register (CSV)", type=["csv"], key="up_register")
        with u2:
            up_roster = st.file_uploader("People roster (CSV, optional)", type=["csv"], key="up_roster",
                                         help="Names, approval limits and who has left. Without it, approver "
                                              "authority comes from the approver role column.")
        with u3:
            st.session_state["org"] = st.text_input("Organization name", value=st.session_state["org"])
            st.download_button("Register template", (SAMPLES / "exceptions_template.csv").read_bytes(),
                               "exceptions_template.csv", "text/csv", use_container_width=True)
            st.download_button("Roster template", (SAMPLES / "people_template.csv").read_bytes(),
                               "people_template.csv", "text/csv", use_container_width=True)
        if up is not None and st.session_state.get("up_name") != (up.name, up.size):
            try:
                st.session_state["rows"] = register_rows(parse_register(up.getvalue().decode("utf-8-sig"), model))
                st.session_state["up_name"] = (up.name, up.size)
                st.session_state["editor_version"] += 1
            except (DataError, UnicodeDecodeError) as exc:
                st.error(f"Could not read the register: {exc}")
        if up_roster is not None:
            st.session_state["roster_text"] = up_roster.getvalue().decode("utf-8-sig")

rows = st.session_state["rows"]
if not rows:
    st.info("No exceptions yet. Upload a register above, or open **Edit register** and add your first exception.")

roster = None
if st.session_state.get("roster_text"):
    try:
        roster = parse_roster(st.session_state["roster_text"], model)
    except DataError as exc:
        st.error(f"Could not read the people roster: {exc}")

report = None
if rows:
    try:
        report = assess(rows_to_register(rows, model), st.session_state["org"], model, as_of, roster)
    except DataError as exc:
        st.error(f"The register has a problem: {exc}")

view = choose("View", VIEWS, key="view")
st.write("")

# ---------------------------------------------------------------- views
if view == "Overview" and report:
    h, c = report.health(), report.counts()
    g, t = st.columns([1, 2.6])
    with g:
        st.markdown(gauge(h["score"], h["label"]), unsafe_allow_html=True)
        with st.expander("How is this scored?"):
            w = model["weights"]
            st.markdown(f"Each active exception is weighted by risk level (critical {w['critical']}, high {w['high']}, "
                        f"medium {w['medium']}, low {w['low']}; unrated counts as high). It counts in full if its worst "
                        f"finding is low or none, half if medium, and not at all if high or critical. "
                        f"Score = governed weight ÷ total weight = **{h['governed_weight']:g} ÷ {h['total_weight']}**.")
    with t:
        k = st.columns(4)
        k[0].markdown(tile(c["active"], "Active exceptions"), unsafe_allow_html=True)
        k[1].markdown(tile(c["lanes"]["Expired, still open"], "Expired but still open"), unsafe_allow_html=True)
        k[2].markdown(tile(c["lanes"]["Expiring soon"], f"Expire within {model['expiring_soon_days']} days"),
                      unsafe_allow_html=True)
        k[3].markdown(tile(c["accepted_risk_load"], "Accepted risk load"), unsafe_allow_html=True)
        st.write("")
        owners = pd.DataFrame(report.by_owner())
        if not owners.empty:
            st.markdown("**Who holds the accepted risk**")
            st.dataframe(owners.rename(columns={"owner": "Risk owner", "exceptions": "Active", "risk_load": "Risk load",
                                                "expired": "Expired", "findings": "Findings"}),
                         hide_index=True, use_container_width=True)
    st.markdown(f"#### What needs fixing ({len(report.findings)})")
    present = [s for s in SEV_ORDER if c["findings"][s]]
    picked = (st.pills("Severity", present, selection_mode="multi", default=present, key="sev_filter",
                       label_visibility="collapsed") if hasattr(st, "pills") and present else present) or []
    shown = [f for f in report.findings if f.severity in picked]
    if not report.findings:
        st.success("No findings. Every active exception is well governed.")
    for f in shown:
        refs = " · ".join(x for x in ("NIST " + ", ".join(f.nist), "ISO 27001 " + ", ".join(f.iso),
                                      "CSF 2.0 " + ", ".join(f.csf)))
        st.markdown(f'<div class="rx-find">{pill(f.severity, SEV_COLORS[f.severity])}'
                    f'<span class="h">{escape(f.exception_id)} · {escape(f.title)}</span>'
                    f'<div class="d">{escape(f.exception_title)}: {escape(f.detail)}</div>'
                    f'<div class="f">Fix: {escape(f.fix)}</div><div class="r">{escape(f.rule_id)} · {escape(refs)}</div></div>',
                    unsafe_allow_html=True)
    notes = [f"{r.exception.exception_id}: {n}" for r in report.results for n in r.not_assessed]
    if notes:
        with st.expander(f"Not assessed ({len(notes)})"):
            st.markdown("\n".join(f"- {n}" for n in notes))
    if roster is None:
        st.caption("No people roster loaded, so approver authority comes from the approver role column and "
                   "departed staff can't be checked.")

elif view == "Lifecycle board" and report:
    st.caption("Every exception, by where it sits in its life. Cards show the risk level, owner, expiry and how many "
               "governance findings it has.")
    cols = st.columns(len(LANES))
    for col, lane in zip(cols, LANES):
        items = [r for r in report.results if r.lane == lane]
        with col:
            st.markdown(f'<div class="rx-lanehead" style="border-top-color:{LANE_COLORS[lane]}">{escape(lane)} '
                        f'<span style="color:#667085;font-weight:500">({len(items)})</span></div>', unsafe_allow_html=True)
            if not items:
                st.markdown('<div class="rx-empty">Nothing here.</div>', unsafe_allow_html=True)
            for r in items:
                e = r.exception
                risk = e.risk_level or "unrated"
                risk_color = SEV_COLORS.get(risk, "#98A2B3")
                if e.expiry_date and r.days_to_expiry is not None and e.status == "active":
                    when = (f"expired {-r.days_to_expiry} days ago" if r.days_to_expiry < 0
                            else f"expires in {r.days_to_expiry} days")
                elif e.status == "closed":
                    when = f"closed {e.closed_date.isoformat()}" if e.closed_date else "closed"
                elif e.status == "pending":
                    when = "awaiting approval"
                else:
                    when = "no expiry date"
                badge = (pill(f"{len(r.findings)} finding{'s' if len(r.findings) != 1 else ''}", SEV_COLORS[r.worst])
                         if r.findings else (pill("well governed", "#1F6F5C") if e.status == "active" else ""))
                st.markdown(f'<div class="rx-card" style="border-left-color:{LANE_COLORS[lane]}">'
                            f'<div class="id">{escape(e.exception_id)}</div><div class="t">{escape(e.title)}</div>'
                            f'{pill(risk, risk_color)}{badge}'
                            f'<div class="m" style="margin-top:6px">Owner: {escape(e.risk_owner or "none")}<br>{escape(when)}</div>'
                            f'</div>', unsafe_allow_html=True)
                if r.findings:
                    with st.expander("Findings", expanded=False):
                        for f in r.findings:
                            st.markdown(f"**{f.rule_id}** ({f.severity}) {f.title}. {f.detail}")

elif view == "Expiry timeline" and report:
    show_closed = st.toggle("Include closed exceptions", value=False)
    st.markdown(f'<div style="background:#fff;border:1px solid #E4E7EC;border-radius:12px;padding:12px">'
                f'{timeline_svg(report, include_closed=show_closed)}</div>', unsafe_allow_html=True)
    st.caption(f"Bars run from approval to expiry. Red: expired but still open. Amber: expires within "
               f"{model['expiring_soon_days']} days. Dashed: no expiry date. A diamond marks an exception that was "
               f"never approved. The dot beside a name shows its most severe finding.")
    upcoming = sorted((r for r in report.active if r.days_to_expiry is not None and 0 <= r.days_to_expiry <= 90),
                      key=lambda r: r.days_to_expiry)
    st.markdown("#### Coming up in the next 90 days")
    if upcoming:
        st.dataframe(pd.DataFrame([{"Expires": r.exception.expiry_date, "In (days)": r.days_to_expiry,
                                    "Exception": f"{r.exception.exception_id} {r.exception.title}",
                                    "Risk owner": r.exception.risk_owner, "Risk": r.exception.risk_level or "unrated"}
                                   for r in upcoming]), hide_index=True, use_container_width=True)
    else:
        st.markdown('<div class="rx-empty">No active exceptions expire in the next 90 days.</div>', unsafe_allow_html=True)

elif view == "Edit register":
    st.caption("Add, change or delete exceptions directly in the table, then press **Check the register**. "
               "Download the register when you're done; nothing is saved on the server.")
    if st.session_state.get("flash"):
        st.success(st.session_state.pop("flash"))
    levels = model["risk_levels"]
    frame = pd.DataFrame(rows, columns=REGISTER_COLUMNS)
    for col in ("approved_date", "expiry_date", "control_verified_date", "remediation_due", "closed_date"):
        frame[col] = pd.to_datetime(frame[col], errors="coerce").dt.date
    cc = st.column_config
    edited = st.data_editor(
        frame, key=f"editor_{st.session_state['editor_version']}", num_rows="dynamic", use_container_width=True,
        hide_index=True, height=440,
        column_config={
            "exception_id": cc.TextColumn("ID", required=True, width="small"),
            "title": cc.TextColumn("Exception", width="medium"),
            "risk_level": cc.SelectboxColumn("Risk", options=levels),
            "status": cc.SelectboxColumn("Status", options=["active", "pending", "closed"], default="active"),
            "approved_date": cc.DateColumn("Approved"),
            "expiry_date": cc.DateColumn("Expires"),
            "control_verified_date": cc.DateColumn("Control verified"),
            "remediation_due": cc.DateColumn("Fix due"),
            "closed_date": cc.DateColumn("Closed"),
            "renewal_count": cc.NumberColumn("Renewals", min_value=0, step=1, default=0),
        })
    b1, b2, _ = st.columns([1.2, 1.2, 3])
    with b1:
        if st.button("Check the register", type="primary", use_container_width=True):
            new_rows = edited.to_dict("records")
            try:
                rows_to_register(new_rows, model)
                st.session_state["rows"] = new_rows
                # Start a fresh editor on the saved rows, so the same edits are not applied twice.
                st.session_state["editor_version"] += 1
                st.session_state["flash"] = f"Register checked: {len(new_rows)} exceptions. Open Overview to see the results."
                st.rerun()
            except DataError as exc:
                st.error(f"Please fix this first: {exc}")
    with b2:
        st.download_button("Download register (CSV)", rows_to_csv(edited.to_dict("records")),
                           "exception_register.csv", "text/csv", use_container_width=True)

elif view == "Acceptance memo" and report:
    st.caption("A one-page risk acceptance memo for signature, built from the register. Any open governance "
               "issues are listed so they're fixed before anyone signs.")
    options = {f"{r.exception.exception_id} · {r.exception.title}": r for r in report.results if r.exception.status != "closed"}
    if options:
        choice = st.selectbox("Exception", list(options))
        res = options[choice]
        m1, m2, _ = st.columns([1.2, 1.2, 3])
        m1.download_button("Download memo (Word-friendly HTML)",
                           acceptance_memo(res, report.organization, report.as_of, fmt="html"),
                           f"risk_acceptance_{res.exception.exception_id}.html", "text/html", use_container_width=True)
        m2.download_button("Download memo (Markdown)", acceptance_memo(res, report.organization, report.as_of),
                           f"risk_acceptance_{res.exception.exception_id}.md", "text/markdown", use_container_width=True)
        with st.container(border=True):
            st.markdown(acceptance_memo(res, report.organization, report.as_of))
    else:
        st.info("There are no open exceptions to write a memo for.")

# ---------------------------------------------------------------- downloads and footer
if report:
    st.divider()
    st.markdown("**Download the review**")
    d = st.columns(4)
    names = {"html": ("HTML report", "text/html"), "md": ("Markdown", "text/markdown"),
             "csv": ("Findings CSV", "text/csv"), "json": ("JSON", "application/json")}
    slug = "".join(ch if ch.isalnum() else "_" for ch in report.organization.lower()).strip("_")
    for col, (fmt, (label, mime)) in zip(d, names.items()):
        col.download_button(label, WRITERS[fmt](report), f"exception_review_{slug}.{fmt}", mime, use_container_width=True)

st.caption(f"Risk Exception Tracker {__version__} · Edward Owusu, CISA · "
           "[Source on GitHub](https://github.com/Edward-Owusu/risk-exception-tracker) · Checks how exceptions are "
           "governed; it does not judge whether accepting a risk was the right business decision. On the hosted app, "
           "data is processed in memory and not saved. For sensitive registers, run it locally.")
