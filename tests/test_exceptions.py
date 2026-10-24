import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from risk_exceptions import cli  # noqa: E402
from risk_exceptions.engine import (  # noqa: E402
    REGISTER_COLUMNS, DataError, assess, load_model, load_register, load_roster, parse_register, parse_roster,
)
from risk_exceptions.reporting import WRITERS, acceptance_memo, timeline_svg  # noqa: E402
from risk_exceptions.table import register_rows, rows_to_csv, rows_to_register  # noqa: E402

SAMPLES = ROOT / "samples"
AS_OF = date(2026, 10, 24)
HEADER = ",".join(REGISTER_COLUMNS)


def one(**fields) -> str:
    """A register with one exception: a clean, well-governed high-risk exception unless fields override it."""
    base = {
        "exception_id": "EX-1", "title": "Test exception", "risk_level": "high", "requested_by": "Ann Requester",
        "risk_owner": "Olu Owner", "approved_by": "Dee Director", "approver_role": "Director",
        "approved_date": "2026-09-01", "expiry_date": "2027-02-01", "compensating_control": "Isolated network",
        "control_verified_date": "2026-10-01", "remediation_plan": "Upgrade", "remediation_due": "2027-01-15",
        "renewal_count": "0", "status": "active",
    }
    base.update(fields)
    return HEADER + "\n" + ",".join(f'"{base.get(c, "")}"' for c in REGISTER_COLUMNS) + "\n"


def run(text: str, roster: str | None = None, model: dict | None = None):
    model = model or load_model()
    r = assess(parse_register(text, model), "Test", model, AS_OF, parse_roster(roster, model) if roster else None)
    return r, {f.rule_id for f in r.findings}


class CleanException(unittest.TestCase):
    def test_well_governed_exception_has_no_findings(self):
        r, ids = run(one())
        self.assertEqual(ids, set())
        self.assertEqual(r.results[0].governance, "Well governed")
        self.assertEqual(r.health()["score"], 100.0)


class Rules(unittest.TestCase):
    def test_re01_missing_approval_is_critical(self):
        r, ids = run(one(approved_by="", approved_date=""))
        self.assertIn("RE-01", ids)
        self.assertEqual(r.findings[0].severity, "critical")
        self.assertIn("are missing", r.findings[0].detail)

    def test_re02_expired_high_risk_is_critical_and_medium_is_high(self):
        r, _ = run(one(expiry_date="2026-10-01"))
        f = [f for f in r.findings if f.rule_id == "RE-02"][0]
        self.assertEqual(f.severity, "critical")
        self.assertEqual(r.results[0].lane, "Expired, still open")
        r, _ = run(one(expiry_date="2026-10-01", risk_level="medium"))
        self.assertEqual([f for f in r.findings if f.rule_id == "RE-02"][0].severity, "high")

    def test_re03_no_expiry(self):
        _, ids = run(one(expiry_date=""))
        self.assertIn("RE-03", ids)

    def test_re04_duration_over_limit_uses_model(self):
        _, ids = run(one(approved_date="2026-01-01", expiry_date="2026-12-31"))
        self.assertIn("RE-04", ids)
        model = load_model(overrides={"max_duration_days": {"high": 400}})
        _, ids = run(one(approved_date="2026-01-01", expiry_date="2026-12-31"), model=model)
        self.assertNotIn("RE-04", ids)

    def test_re05_authority_from_role_and_roster(self):
        _, ids = run(one(approver_role="IT Manager"))
        self.assertIn("RE-05", ids)
        _, ids = run(one(approver_role="Unknown title"))
        self.assertIn("RE-05", ids)  # authority not evidenced
        roster = "name,title,approval_limit,status,left_date\nDee Director,Director,medium,active,\n"
        r, ids = run(one(), roster)
        self.assertIn("RE-05", ids)
        self.assertIn("(roster)", [f for f in r.findings if f.rule_id == "RE-05"][0].detail)

    def test_re05_unrated_risk_cannot_show_authority(self):
        _, ids = run(one(risk_level=""))
        self.assertIn("RE-05", ids)

    def test_re06_self_approval_is_case_insensitive(self):
        _, ids = run(one(requested_by="dee  director"))
        self.assertIn("RE-06", ids)

    def test_re07_no_owner_and_owner_left(self):
        _, ids = run(one(risk_owner=""))
        self.assertIn("RE-07", ids)
        roster = ("name,title,approval_limit,status,left_date\nDee Director,Director,high,active,\n"
                  "Olu Owner,Engineer,none,left,2026-05-01\n")
        _, ids = run(one(), roster)
        self.assertIn("RE-07", ids)

    def test_re08_approver_left_only_with_roster(self):
        roster = "name,title,approval_limit,status,left_date\nDee Director,Director,high,left,2026-06-30\nOlu Owner,,,active,\n"
        _, ids = run(one(), roster)
        self.assertIn("RE-08", ids)
        _, ids = run(one())
        self.assertNotIn("RE-08", ids)

    def test_person_leaving_in_future_has_not_left(self):
        roster = "name,title,approval_limit,status,left_date\nDee Director,Director,high,left,2026-12-31\nOlu Owner,,,active,\n"
        _, ids = run(one(), roster)
        self.assertNotIn("RE-08", ids)

    def test_re09_compensating_control_only_for_high_and_critical(self):
        _, ids = run(one(compensating_control="", control_verified_date=""))
        self.assertIn("RE-09", ids)
        _, ids = run(one(compensating_control="", control_verified_date="", risk_level="medium",
                         approver_role="Manager"))
        self.assertNotIn("RE-09", ids)

    def test_re10_control_verification(self):
        _, ids = run(one(control_verified_date=""))
        self.assertIn("RE-10", ids)
        _, ids = run(one(control_verified_date="2026-05-01"))
        self.assertIn("RE-10", ids)

    def test_re11_remediation(self):
        _, ids = run(one(remediation_plan=""))
        self.assertIn("RE-11", ids)
        _, ids = run(one(remediation_due="2026-10-01"))
        self.assertIn("RE-11", ids)

    def test_re12_renewals(self):
        _, ids = run(one(renewal_count="3"))
        self.assertIn("RE-12", ids)
        _, ids = run(one(renewal_count="2"))
        self.assertNotIn("RE-12", ids)

    def test_re13_expiring_soon_is_low_and_does_not_lower_health(self):
        r, ids = run(one(expiry_date="2026-11-10"))
        self.assertEqual(ids, {"RE-13"})
        self.assertEqual(r.results[0].lane, "Expiring soon")
        self.assertEqual(r.health()["score"], 100.0)

    def test_pending_and_closed_are_not_checked(self):
        r, ids = run(one(status="closed", expiry_date="2025-01-01", approved_by=""))
        self.assertEqual(ids, set())
        self.assertEqual(r.results[0].lane, "Closed")
        r, ids = run(one(status="pending", approved_by="", approved_date=""))
        self.assertEqual(ids, set())
        self.assertEqual(r.results[0].lane, "Pending approval")


class Scoring(unittest.TestCase):
    def test_health_weights_by_risk_and_worst_finding(self):
        text = one() + one(exception_id="EX-2", risk_level="critical", approver_role="CEO",
                           expiry_date="2026-11-20", approved_date="2026-09-01").split("\n", 1)[1]
        text += one(exception_id="EX-3", risk_level="low", approver_role="Manager", remediation_plan="",
                    compensating_control="", control_verified_date="").split("\n", 1)[1]
        r, _ = run(text)
        # EX-1 high, clean (6); EX-2 critical, expiring soon only (10); EX-3 low, medium finding (1 x 0.5)
        h = r.health()
        self.assertEqual(h["total_weight"], 17)
        self.assertEqual(h["governed_weight"], 16.5)
        self.assertAlmostEqual(h["score"], round(100 * 16.5 / 17, 1))

    def test_unrated_risk_weighted_as_high(self):
        r, _ = run(one(risk_level=""))
        self.assertEqual(r.counts()["accepted_risk_load"], 6)


class Parsing(unittest.TestCase):
    def test_bad_values_raise_clear_errors(self):
        with self.assertRaises(DataError):
            parse_register(one(risk_level="severe"))
        with self.assertRaises(DataError):
            parse_register(one(status="open"))
        with self.assertRaises(DataError):
            parse_register(one(expiry_date="next year"))
        with self.assertRaises(DataError):
            parse_register(one() + one().split("\n", 1)[1])
        with self.assertRaises(DataError):
            parse_register("title\nNo id column\n")

    def test_us_dates_are_accepted(self):
        e = parse_register(one(expiry_date="02/01/2027"))[0]
        self.assertEqual(e.expiry_date, date(2027, 2, 1))


class Samples(unittest.TestCase):
    def test_riverbend_is_weak_and_northfield_is_strong(self):
        weak = assess(load_register(SAMPLES / "riverbend_components_exceptions.csv"), "R", as_of=AS_OF,
                      roster=load_roster(SAMPLES / "riverbend_components_people.csv"))
        strong = assess(load_register(SAMPLES / "northfield_cold_logistics_exceptions.csv"), "N", as_of=AS_OF,
                        roster=load_roster(SAMPLES / "northfield_cold_logistics_people.csv"))
        self.assertLess(weak.health()["score"], 40)
        self.assertGreater(strong.health()["score"], 75)
        rules_hit = {f.rule_id for f in weak.findings}
        self.assertEqual(rules_hit, {f"RE-{i:02d}" for i in range(1, 14)})  # every rule is exercised

    def test_template_loads(self):
        self.assertEqual(len(load_register(SAMPLES / "exceptions_template.csv")), 1)
        self.assertEqual(len(load_roster(SAMPLES / "people_template.csv")), 2)


class Outputs(unittest.TestCase):
    def setUp(self):
        self.report = assess(load_register(SAMPLES / "riverbend_components_exceptions.csv"), "Riverbend", as_of=AS_OF,
                             roster=load_roster(SAMPLES / "riverbend_components_people.csv"))

    def test_all_writers_and_timeline(self):
        for fmt, writer in WRITERS.items():
            self.assertTrue(writer(self.report), fmt)
        svg = timeline_svg(self.report)
        self.assertTrue(svg.startswith("<svg") and "as of 2026-10-24" in svg)

    def test_memo_lists_open_issues(self):
        res = [r for r in self.report.results if r.exception.exception_id == "EX-2025-003"][0]
        md = acceptance_memo(res, "Riverbend", AS_OF)
        self.assertIn("Open governance issues", md)
        self.assertIn("RE-02", md)
        self.assertIn("<html", acceptance_memo(res, "Riverbend", AS_OF, fmt="html"))

    def test_table_round_trip(self):
        rows = register_rows([r.exception for r in self.report.results])
        again = rows_to_register(rows)
        self.assertEqual([e.exception_id for e in again], [r["exception_id"] for r in rows])
        self.assertIn("2026-02-10", rows_to_csv(rows))
        rows[0]["renewal_count"] = 2.0
        rows[0]["closed_date"] = float("nan")
        self.assertEqual(rows_to_register(rows)[0].renewal_count, 2)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as out:
            args = [str(SAMPLES / "riverbend_components_exceptions.csv"), "--roster",
                    str(SAMPLES / "riverbend_components_people.csv"), "--as-of", "2026-10-24", "--out", out,
                    "--memo", "EX-2026-002"]
            self.assertEqual(cli.main(args), 0)
            self.assertEqual(cli.main(args + ["--fail-on", "critical"]), 2)
            self.assertTrue((Path(out) / "memo_EX-2026-002.md").exists())
            self.assertEqual(cli.main([str(SAMPLES / "northfield_cold_logistics_exceptions.csv"), "--as-of",
                                       "2026-10-24", "--out", out, "--fail-on", "high", "--roster",
                                       str(SAMPLES / "northfield_cold_logistics_people.csv")]), 0)


if __name__ == "__main__":
    unittest.main()
