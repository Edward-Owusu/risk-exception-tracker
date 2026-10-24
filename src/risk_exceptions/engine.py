"""Load a risk exception register and check how each exception is governed."""

from __future__ import annotations

import csv
import io
import json
from dataclasses import asdict, dataclass, field
from datetime import date, datetime
from pathlib import Path
from typing import Any

DATA = Path(__file__).parent / "data"
SEV_ORDER = ["critical", "high", "medium", "low"]
STATUSES = ("active", "pending", "closed")
LANES = ["Expired, still open", "Expiring soon", "Active", "Pending approval", "Closed"]

REGISTER_COLUMNS = [
    "exception_id", "title", "policy_or_standard", "control_refs", "scope", "reason", "risk_level",
    "requested_by", "risk_owner", "approved_by", "approver_role", "approved_date", "expiry_date",
    "compensating_control", "control_verified_date", "remediation_plan", "remediation_due",
    "renewal_count", "status", "closed_date",
]
ROSTER_COLUMNS = ["name", "title", "approval_limit", "status", "left_date"]


class DataError(ValueError):
    """Raised when an input file cannot be read."""


# ---------------------------------------------------------------- model and rules

def load_model(path: str | Path | None = None, overrides: dict | None = None) -> dict:
    model = json.loads((DATA / "model.json").read_text(encoding="utf-8"))
    extra = dict(overrides or {})
    if path:
        extra = {**json.loads(Path(path).read_text(encoding="utf-8")), **extra}
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(model.get(key), dict):
            model[key] = {**model[key], **value}
        else:
            model[key] = value
    return model


def load_rules() -> dict[str, dict]:
    return {r["id"]: r for r in json.loads((DATA / "rules.json").read_text(encoding="utf-8"))["rules"]}


# ---------------------------------------------------------------- parsing helpers

def parse_date(value: str, col: str = "date", row: int | None = None) -> date | None:
    v = (value or "").strip()
    if not v:
        return None
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%d %b %Y", "%d %B %Y"):
        try:
            return datetime.strptime(v, fmt).date()
        except ValueError:
            pass
    where = f"Row {row}: " if row else ""
    raise DataError(f"{where}'{col}' must be a date like 2026-10-24, got '{v}'.")


def _norm(name: str) -> str:
    return " ".join((name or "").lower().split())


def _read_csv(text: str, required: str) -> list[tuple[int, dict[str, str]]]:
    reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
    fields = [(f or "").strip().lower() for f in (reader.fieldnames or [])]
    if required not in fields:
        raise DataError(f"The file needs a header row with at least a '{required}' column.")
    rows = []
    for i, raw in enumerate(reader, start=2):
        rows.append((i, {(k or "").strip().lower(): (v or "").strip() for k, v in raw.items() if k is not None}))
    return rows


# ---------------------------------------------------------------- data classes

@dataclass
class Person:
    name: str
    title: str = ""
    approval_limit: str | None = None
    status: str = "active"
    left_date: date | None = None

    def has_left(self, as_of: date) -> bool:
        if self.status == "left":
            return self.left_date is None or self.left_date <= as_of
        return False


@dataclass
class Exception_:
    exception_id: str
    title: str
    policy_or_standard: str = ""
    control_refs: str = ""
    scope: str = ""
    reason: str = ""
    risk_level: str | None = None
    requested_by: str = ""
    risk_owner: str = ""
    approved_by: str = ""
    approver_role: str = ""
    approved_date: date | None = None
    expiry_date: date | None = None
    compensating_control: str = ""
    control_verified_date: date | None = None
    remediation_plan: str = ""
    remediation_due: date | None = None
    renewal_count: int = 0
    status: str = "active"
    closed_date: date | None = None


def parse_register(text: str, model: dict | None = None) -> list[Exception_]:
    model = model or load_model()
    levels = model["risk_levels"]
    out, seen = [], set()
    for i, r in _read_csv(text, "exception_id"):
        eid = r.get("exception_id", "")
        if not eid:
            continue
        if eid.lower() in seen:
            raise DataError(f"Row {i}: exception '{eid}' appears more than once.")
        seen.add(eid.lower())
        risk = (r.get("risk_level") or "").lower() or None
        if risk and risk not in levels:
            raise DataError(f"Row {i}: 'risk_level' must be one of {', '.join(levels)}, got '{risk}'.")
        status = (r.get("status") or "active").lower()
        if status not in STATUSES:
            raise DataError(f"Row {i}: 'status' must be one of {', '.join(STATUSES)}, got '{status}'.")
        renewals = r.get("renewal_count") or "0"
        try:
            renewals = int(float(renewals))
        except ValueError:
            raise DataError(f"Row {i}: 'renewal_count' must be a whole number, got '{renewals}'.")
        out.append(Exception_(
            exception_id=eid,
            title=r.get("title", "") or eid,
            policy_or_standard=r.get("policy_or_standard", ""),
            control_refs=r.get("control_refs", ""),
            scope=r.get("scope", ""),
            reason=r.get("reason", ""),
            risk_level=risk,
            requested_by=r.get("requested_by", ""),
            risk_owner=r.get("risk_owner", ""),
            approved_by=r.get("approved_by", ""),
            approver_role=r.get("approver_role", ""),
            approved_date=parse_date(r.get("approved_date", ""), "approved_date", i),
            expiry_date=parse_date(r.get("expiry_date", ""), "expiry_date", i),
            compensating_control=r.get("compensating_control", ""),
            control_verified_date=parse_date(r.get("control_verified_date", ""), "control_verified_date", i),
            remediation_plan=r.get("remediation_plan", ""),
            remediation_due=parse_date(r.get("remediation_due", ""), "remediation_due", i),
            renewal_count=max(renewals, 0),
            status=status,
            closed_date=parse_date(r.get("closed_date", ""), "closed_date", i),
        ))
    if not out:
        raise DataError("The register has no exceptions. Each row needs an 'exception_id'.")
    return out


def parse_roster(text: str, model: dict | None = None) -> dict[str, Person]:
    model = model or load_model()
    levels = model["risk_levels"]
    people: dict[str, Person] = {}
    for i, r in _read_csv(text, "name"):
        name = r.get("name", "")
        if not name:
            continue
        limit = (r.get("approval_limit") or "").lower() or None
        if limit in ("none", "no", "n/a"):
            limit = "none"
        elif limit and limit not in levels:
            raise DataError(f"Roster row {i}: 'approval_limit' must be none or one of {', '.join(levels)}, got '{limit}'.")
        status = (r.get("status") or "active").lower()
        if status not in ("active", "left"):
            raise DataError(f"Roster row {i}: 'status' must be active or left, got '{status}'.")
        people[_norm(name)] = Person(name, r.get("title", ""), limit, status,
                                     parse_date(r.get("left_date", ""), "left_date", i))
    return people


def load_register(path: str | Path, model: dict | None = None) -> list[Exception_]:
    return parse_register(Path(path).read_text(encoding="utf-8-sig"), model)


def load_roster(path: str | Path, model: dict | None = None) -> dict[str, Person]:
    return parse_roster(Path(path).read_text(encoding="utf-8-sig"), model)


# ---------------------------------------------------------------- results

@dataclass
class Finding:
    rule_id: str
    title: str
    severity: str
    exception_id: str
    exception_title: str
    detail: str
    fix: str
    nist: list[str]
    iso: list[str]
    csf: list[str]


@dataclass
class ExceptionResult:
    exception: Exception_
    lane: str
    days_to_expiry: int | None
    findings: list[Finding] = field(default_factory=list)
    not_assessed: list[str] = field(default_factory=list)

    @property
    def worst(self) -> str | None:
        return min((f.severity for f in self.findings), key=SEV_ORDER.index, default=None)

    @property
    def governance(self) -> str:
        if self.exception.status != "active":
            return "Not checked"
        w = self.worst
        if w == "critical":
            return "Out of control"
        if w == "high":
            return "Weak"
        if w == "medium":
            return "Needs attention"
        return "Well governed"


@dataclass
class Report:
    organization: str
    as_of: date
    results: list[ExceptionResult]
    model: dict
    roster_used: bool

    @property
    def active(self) -> list[ExceptionResult]:
        return [r for r in self.results if r.exception.status == "active"]

    @property
    def findings(self) -> list[Finding]:
        out = [f for r in self.results for f in r.findings]
        return sorted(out, key=lambda f: (SEV_ORDER.index(f.severity), f.exception_id, f.rule_id))

    def _weight(self, r: ExceptionResult) -> int:
        # An exception with no risk level is weighted as high: the risk was never rated, so it can't be assumed small.
        return self.model["weights"][r.exception.risk_level or "high"]

    @staticmethod
    def credit(r: ExceptionResult) -> float:
        """Share of an exception's weight counted as well governed: 1 if its worst finding is low or none,
        0.5 if medium, 0 if high or critical."""
        return {"critical": 0.0, "high": 0.0, "medium": 0.5}.get(r.worst or "", 1.0)

    def health(self) -> dict[str, Any]:
        active = self.active
        total = sum(self._weight(r) for r in active)
        good = sum(self._weight(r) * self.credit(r) for r in active)
        score = round(100 * good / total, 1) if total else 100.0
        label = next(b["label"] for b in self.model["health_bands"] if score >= b["min"])
        return {"score": score, "label": label, "governed_weight": round(good, 1), "total_weight": total}

    def counts(self) -> dict[str, Any]:
        active = self.active
        by_risk = {lvl: sum(1 for r in active if r.exception.risk_level == lvl) for lvl in self.model["risk_levels"]}
        by_risk["unrated"] = sum(1 for r in active if not r.exception.risk_level)
        lanes = {lane: sum(1 for r in self.results if r.lane == lane) for lane in LANES}
        sev = {s: sum(1 for f in self.findings if f.severity == s) for s in SEV_ORDER}
        return {
            "total": len(self.results),
            "active": len(active),
            "by_risk": by_risk,
            "lanes": lanes,
            "findings": sev,
            "accepted_risk_load": sum(self._weight(r) for r in active),
        }

    def by_owner(self) -> list[dict[str, Any]]:
        rows: dict[str, dict[str, Any]] = {}
        for r in self.active:
            owner = r.exception.risk_owner or "(no owner)"
            row = rows.setdefault(owner, {"owner": owner, "exceptions": 0, "risk_load": 0, "findings": 0, "expired": 0})
            row["exceptions"] += 1
            row["risk_load"] += self._weight(r)
            row["findings"] += len(r.findings)
            row["expired"] += r.lane == LANES[0]
        return sorted(rows.values(), key=lambda x: (-x["risk_load"], x["owner"]))

    def to_dict(self) -> dict[str, Any]:
        def enc(o):
            if isinstance(o, date):
                return o.isoformat()
            if isinstance(o, dict):
                return {k: enc(v) for k, v in o.items()}
            if isinstance(o, list):
                return [enc(v) for v in o]
            return o
        return enc({
            "organization": self.organization,
            "as_of": self.as_of,
            "health": self.health(),
            "counts": self.counts(),
            "exceptions": [{**asdict(r.exception), "lane": r.lane, "governance": r.governance,
                            "days_to_expiry": r.days_to_expiry, "not_assessed": r.not_assessed,
                            "findings": [asdict(f) for f in r.findings]} for r in self.results],
        })


# ---------------------------------------------------------------- the checks

def _authority(e: Exception_, roster: dict[str, Person] | None, model: dict) -> tuple[str | None, str]:
    """Return the highest risk level the approver may accept, and where that came from."""
    if roster is not None:
        person = roster.get(_norm(e.approved_by))
        if person and person.approval_limit:
            return person.approval_limit, "roster"
        if person and person.title:
            role = _norm(person.title)
            if role in model["authority_by_role"]:
                return model["authority_by_role"][role], "roster title"
    role = _norm(e.approver_role)
    if role in model["authority_by_role"]:
        return model["authority_by_role"][role], "approver role"
    return None, ""


def _lane(e: Exception_, as_of: date, model: dict) -> str:
    if e.status == "closed":
        return "Closed"
    if e.status == "pending":
        return "Pending approval"
    if e.expiry_date and e.expiry_date < as_of:
        return "Expired, still open"
    if e.expiry_date and (e.expiry_date - as_of).days <= model["expiring_soon_days"]:
        return "Expiring soon"
    return "Active"


def check_exception(e: Exception_, as_of: date, model: dict, rules: dict[str, dict],
                    roster: dict[str, Person] | None = None) -> ExceptionResult:
    days = (e.expiry_date - as_of).days if e.expiry_date else None
    res = ExceptionResult(e, _lane(e, as_of, model), days)
    if e.status != "active":
        return res
    levels = model["risk_levels"]
    risk = e.risk_level

    def add(rule_id: str, detail: str, severity: str | None = None) -> None:
        r = rules[rule_id]
        sev = severity or r["severity"]
        if risk and risk in r.get("critical_when_risk", []):
            sev = "critical"
        res.findings.append(Finding(rule_id, r["title"], sev, e.exception_id, e.title, detail, r["fix"],
                                    r["nist"], r["iso"], r["csf"]))

    approved = bool(e.approved_by and e.approved_date)

    # RE-01 approval recorded
    if not approved:
        missing = " and ".join(x for x, v in (("approver", e.approved_by), ("approval date", e.approved_date)) if not v)
        verb = "are" if " and " in missing else "is"
        add("RE-01", f"Marked active, but the {missing} {verb} missing.")

    # RE-02 expired / RE-03 no expiry / RE-13 expiring soon
    if e.expiry_date is None:
        add("RE-03", "No expiry date is recorded, so the exception never comes back for review.")
    elif e.expiry_date < as_of:
        add("RE-02", f"Expired on {e.expiry_date.isoformat()} ({-days} days ago) but is still marked active.")
    elif days is not None and days <= model["expiring_soon_days"]:
        add("RE-13", f"Expires on {e.expiry_date.isoformat()}, in {days} days.")

    # RE-04 duration
    if risk and e.approved_date and e.expiry_date:
        allowed = model["max_duration_days"][risk]
        length = (e.expiry_date - e.approved_date).days
        if length > allowed:
            add("RE-04", f"Approved for {length} days; the maximum for {risk} risk is {allowed} days.")
    elif e.expiry_date and e.approved_date:
        res.not_assessed.append("RE-04: no risk level, so the allowed duration is unknown")

    # RE-05 approver authority
    if e.approved_by:
        if not risk:
            add("RE-05", "The risk was never rated, so no one can show the approver was authorized to accept it.")
        else:
            limit, source = _authority(e, roster, model)
            if limit is None:
                add("RE-05", f"Approver authority is not evidenced: '{e.approved_by}' has no approval limit on record.")
            elif limit == "none" or levels.index(limit) < levels.index(risk):
                shown = "no authority" if limit == "none" else f"authority up to {limit} risk"
                add("RE-05", f"{e.approved_by} has {shown} ({source}), but this exception is {risk} risk.")

    # RE-06 self-approval
    if e.approved_by and e.requested_by and _norm(e.approved_by) == _norm(e.requested_by):
        add("RE-06", f"{e.approved_by} both requested and approved this exception.")

    # RE-07 risk owner / RE-08 approver left
    if not e.risk_owner:
        add("RE-07", "No risk owner is named.")
    elif roster is not None:
        owner = roster.get(_norm(e.risk_owner))
        if owner and owner.has_left(as_of):
            when = f" on {owner.left_date.isoformat()}" if owner.left_date else ""
            add("RE-07", f"Risk owner {e.risk_owner} left the organization{when}.")
        elif owner is None:
            res.not_assessed.append(f"RE-07: risk owner '{e.risk_owner}' is not on the roster")
    if e.approved_by and roster is not None:
        approver = roster.get(_norm(e.approved_by))
        if approver and approver.has_left(as_of):
            when = f" on {approver.left_date.isoformat()}" if approver.left_date else ""
            add("RE-08", f"Approver {e.approved_by} left the organization{when}.")

    # RE-09 / RE-10 compensating control
    needs_control = (risk or "high") in model["compensating_control_required_for"]
    if needs_control and not e.compensating_control:
        what = f"{risk} risk" if risk else "an unrated risk"
        add("RE-09", f"This is {what}, but no compensating control is recorded.")
    if e.compensating_control:
        limit = model["control_verification_days"]
        if e.control_verified_date is None:
            add("RE-10", "A compensating control is recorded but there is no date showing it was ever verified.")
        elif (as_of - e.control_verified_date).days > limit:
            age = (as_of - e.control_verified_date).days
            add("RE-10", f"Compensating control last verified {age} days ago; the limit is {limit} days.")

    # RE-11 remediation
    if not e.remediation_plan:
        add("RE-11", "No plan is recorded to remove the need for this exception.")
    elif e.remediation_due and e.remediation_due < as_of:
        add("RE-11", f"Remediation was due on {e.remediation_due.isoformat()} and the exception is still open.")

    # RE-12 renewals
    if e.renewal_count > model["max_renewals"]:
        add("RE-12", f"Renewed {e.renewal_count} times; the limit is {model['max_renewals']}.")

    res.findings.sort(key=lambda f: (SEV_ORDER.index(f.severity), f.rule_id))
    return res


def assess(exceptions: list[Exception_], organization: str = "Organization", model: dict | None = None,
           as_of: date | None = None, roster: dict[str, Person] | None = None) -> Report:
    model = model or load_model()
    rules = load_rules()
    as_of = as_of or date.today()
    results = [check_exception(e, as_of, model, rules, roster) for e in exceptions]
    lane_order = {lane: i for i, lane in enumerate(LANES)}
    results.sort(key=lambda r: (lane_order[r.lane],
                                SEV_ORDER.index(r.worst) if r.worst else 9,
                                r.exception.expiry_date or date.max,
                                r.exception.exception_id))
    return Report(organization, as_of, results, model, roster is not None)
