# Methodology

## Purpose

Every organization grants exceptions to its security policies: a legacy system that cannot be patched, a vendor that cannot support MFA, a business need that conflicts with a standard. Accepting a risk this way is legitimate, but only while it stays governed: someone with the right authority approved it, a named person owns it, it has an end date, something reduces the risk in the meantime, and there is a plan to remove the need for it.

In practice, exceptions are often granted once and never looked at again. They expire while still in use, the approver or owner leaves, the compensating control quietly stops working, and the same exception is renewed year after year. This tool checks a register of exceptions for exactly those failures.

It supports:

- **NIST Cybersecurity Framework 2.0, ID.RA-07:** "Changes and exceptions are managed, assessed for risk impact, recorded, and tracked."
- **NIST CSF 2.0, ID.RA-06** (risk responses are tracked), **GV.RM-04** (risk response options) and **GV.RR-02** (roles, responsibilities, and authorities).
- **NIST SP 800-53 Rev. 5:** RA-7 (Risk Response), PM-9 (Risk Management Strategy), CA-5 (Plan of Action and Milestones), CA-7 (Continuous Monitoring), CM-6 (approved deviations from configuration settings), and AC-5 (Separation of Duties).
- **ISO/IEC 27001:2022:** clause 6.1.3 (risk treatment, including risk owners' approval of residual risk), clause 9.1 (monitoring), and Annex A 5.3 (segregation of duties).

## Which exceptions are checked

Each exception has a status: **active**, **pending** (requested, not yet approved) or **closed**. Only active exceptions are checked, because they are the ones the organization is relying on. Pending and closed exceptions appear on the board and timeline but produce no findings.

## Lifecycle lanes

| Lane | Rule |
|---|---|
| Expired, still open | Active, with an expiry date before the as-of date |
| Expiring soon | Active, expiring within the expiring-soon window (default 30 days) |
| Active | Any other active exception, including those with no expiry date |
| Pending approval | Status pending |
| Closed | Status closed |

## Checks

| Rule | Finding | Severity | NIST SP 800-53 | ISO 27001 | CSF 2.0 |
|---|---|---|---|---|---|
| RE-01 | Active exception with no approver or approval date | Critical | RA-7, CM-6 | 6.1.3 | ID.RA-07 |
| RE-02 | Expired but still active | High; critical when the risk is high or critical | RA-7, CA-5 | 6.1.3 | ID.RA-07 |
| RE-03 | No expiry date | High | RA-7, PM-9 | 6.1.3 | ID.RA-07 |
| RE-04 | Approved for longer than the maximum for its risk level | Medium | PM-9 | 6.1.3 | GV.RM-04 |
| RE-05 | Approver not authorized for the risk level, or authority not evidenced | High | PM-9, RA-7 | 6.1.3 | GV.RR-02 |
| RE-06 | Requester approved their own exception | High | AC-5, RA-7 | A.5.3 | GV.RR-02 |
| RE-07 | No risk owner, or the owner has left | High | PM-9, RA-7 | 6.1.3 | GV.RR-02 |
| RE-08 | Approver has left the organization | Medium | PM-9 | 6.1.3 | ID.RA-07 |
| RE-09 | High, critical or unrated risk with no compensating control | High | RA-7, CA-5 | 6.1.3 | ID.RA-06 |
| RE-10 | Compensating control never verified, or not verified within the limit (default 90 days) | Medium | CA-7 | 9.1 | ID.RA-06 |
| RE-11 | No remediation plan, or remediation date passed | Medium | CA-5 | 6.1.3 | ID.RA-06 |
| RE-12 | Renewed more times than allowed (default 2) | Medium | PM-9, CA-5 | 6.1.3 | ID.RA-07 |
| RE-13 | Expires within the expiring-soon window | Low | RA-7 | 6.1.3 | ID.RA-07 |

The rule text and fixes are in `src/risk_exceptions/data/rules.json`; the logic is in `src/risk_exceptions/engine.py`.

### Approver authority (RE-05)

Most organizations set who may accept which level of risk, for example a manager up to medium risk and an executive for critical risk. The tool finds the approver's limit in this order:

1. The **people roster**, if supplied: the approver's `approval_limit`, or failing that their job title.
2. The register's **approver_role** column.

Job titles are matched against `authority_by_role` in the model (for example "manager" is medium, "director" high, "ceo" critical). If neither source shows the approver's authority, the finding is raised as "authority not evidenced", in line with the audit principle that a control is not assumed to work without evidence. An exception with no risk rating also fails RE-05, because no one can show the approver was authorized to accept a risk that was never rated.

### People who have left (RE-07, RE-08)

These checks need the optional people roster. A person counts as having left when their status is `left` and their `left_date` is on or before the as-of date (or blank). Without a roster, RE-08 and the "owner has left" part of RE-07 are not run, and the report says so.

### Missing values

A missing value is never treated as compliant. A missing expiry date is a finding (RE-03), a missing verification date is a finding (RE-10), and an unrated risk is weighted as high and treated as needing a compensating control.

## Governance health score

Each active exception is weighted by its risk level: critical 10, high 6, medium 3, low 1, and unrated as high. Each exception earns credit by its most severe finding:

| Worst finding | Credit | Governance label |
|---|---|---|
| None or low | 100% | Well governed |
| Medium | 50% | Needs attention |
| High | 0% | Weak |
| Critical | 0% | Out of control |

```
health = 100 x sum(weight x credit) / sum(weight)
```

Bands: 85 or more Healthy, 65 to 84 Needs attention, 40 to 64 Weak, below 40 Out of control. Weighting by risk means a poorly governed critical exception lowers the score far more than a poorly governed low one, which matches where an auditor or regulator would focus.

**Accepted risk load** is the sum of the weights of all active exceptions. It shows how much risk the organization is carrying through exceptions, regardless of how well each is governed.

## Organization-defined values

The maximum approval period by risk level, the expiring-soon window, the verification interval for compensating controls, the renewal limit, the role-to-authority map, the weights and the bands are all in `src/risk_exceptions/data/model.json`. Copy it, change values, and pass it with `--model`, or adjust the main limits under **Your rules** in the dashboard. Defaults reflect common practice and the author's judgment; they are not taken from a standard.

## Limitations

- The tool checks how exceptions are governed, not whether accepting each risk was the right decision.
- Results depend on the register being complete. Exceptions granted informally (in email or chat) and never recorded cannot be found this way; an auditor should test completeness, for example by tracing known deviations back to the register.
- The tool reads the register as given. It does not confirm that a compensating control works; it checks that someone recorded verifying it.
- It supports, and does not replace, the judgment of a qualified auditor.
