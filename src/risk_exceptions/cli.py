"""Command-line interface.

Examples:
    risk-exceptions samples/riverbend_components_exceptions.csv --roster samples/riverbend_components_people.csv
    risk-exceptions register.csv --as-of 2026-10-24 --format html csv --fail-on high
    risk-exceptions register.csv --memo EX-2026-004
"""

from __future__ import annotations

import argparse
import sys
from datetime import date
from pathlib import Path

from . import __version__
from .engine import SEV_ORDER, DataError, assess, load_model, load_register, load_roster
from .reporting import WRITERS, acceptance_memo


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="risk-exceptions",
                                description="Check a register of security policy exceptions and risk acceptances.")
    p.add_argument("register", help="Path to the exception register CSV")
    p.add_argument("--roster", help="Optional people CSV with approval limits and who has left")
    p.add_argument("--org", help="Organization name for the report (default: file name)")
    p.add_argument("--as-of", help="Date to check expiry and verification against (YYYY-MM-DD, default: today)")
    p.add_argument("--format", nargs="+", choices=sorted(WRITERS), default=["html", "csv"])
    p.add_argument("--out", default="reports", help="Output directory (default: reports)")
    p.add_argument("--model", help="JSON file overriding the scoring model and limits")
    p.add_argument("--memo", metavar="EXCEPTION_ID", help="Also write a risk acceptance memo for this exception")
    p.add_argument("--fail-on", choices=SEV_ORDER, help="Exit with code 2 if any finding is this severe or worse")
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        model = load_model(args.model)
        register = load_register(args.register, model)
        roster = load_roster(args.roster, model) if args.roster else None
        as_of = date.fromisoformat(args.as_of) if args.as_of else None
    except (OSError, DataError, ValueError) as exc:
        print(f"Could not read input: {exc}", file=sys.stderr)
        return 1
    stem = Path(args.register).stem
    org = args.org or stem.replace("_exceptions", "").replace("_", " ").title()
    r = assess(register, org, model, as_of, roster)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    for fmt in args.format:
        path = out / f"{stem}.{fmt}"
        path.write_text(WRITERS[fmt](r), encoding="utf-8")
        print(f"Wrote {path}")
    if args.memo:
        match = [x for x in r.results if x.exception.exception_id.lower() == args.memo.lower()]
        if not match:
            print(f"No exception with ID '{args.memo}' in the register.", file=sys.stderr)
            return 1
        path = out / f"memo_{match[0].exception.exception_id}.md"
        path.write_text(acceptance_memo(match[0], r.organization, r.as_of), encoding="utf-8")
        print(f"Wrote {path}")
    h, c = r.health(), r.counts()
    print(f"\n{r.organization} | as of {r.as_of} | {c['active']} active of {c['total']} exceptions")
    print(f"Governance health: {h['score']:.0f}/100 ({h['label']}) | Expired but open: {c['lanes']['Expired, still open']} | "
          f"Expiring soon: {c['lanes']['Expiring soon']} | Findings: " +
          ", ".join(f"{c['findings'][s]} {s}" for s in SEV_ORDER))
    for f in r.findings[:6]:
        print(f"  [{f.severity.upper():<8}] {f.exception_id} {f.rule_id} {f.title}")
    if len(r.findings) > 6:
        print(f"  ... and {len(r.findings) - 6} more in the report")
    if args.fail_on:
        limit = SEV_ORDER.index(args.fail_on)
        if any(SEV_ORDER.index(f.severity) <= limit for f in r.findings):
            return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
