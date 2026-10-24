# Data reference

## Exception register (required)

One row per exception. Only `exception_id` is required; every other column can be blank, and blank values are treated conservatively (see the methodology). Dates can be written as `2026-10-24` or `10/24/2026`. Start from `samples/exceptions_template.csv`.

| Column | Meaning | Used by |
|---|---|---|
| `exception_id` | Unique ID, for example EX-2026-004 | All |
| `title` | Short description of the exception | Reports |
| `policy_or_standard` | The policy or standard the exception departs from | Memo |
| `control_refs` | Related control IDs, for example "SI-2, SA-22" | Memo |
| `scope` | Systems, people or locations covered | Memo |
| `reason` | Why the policy cannot be met | Memo |
| `risk_level` | low, medium, high or critical (blank = unrated) | RE-02, RE-04, RE-05, RE-09, score |
| `requested_by` | Who asked for the exception | RE-06 |
| `risk_owner` | Who owns the residual risk | RE-07 |
| `approved_by` | Who approved it | RE-01, RE-05, RE-06, RE-08 |
| `approver_role` | Approver's job title, used when there is no roster entry | RE-05 |
| `approved_date` | Date approved | RE-01, RE-04, timeline |
| `expiry_date` | Date the exception ends | RE-02, RE-03, RE-04, RE-13 |
| `compensating_control` | What reduces the risk in the meantime | RE-09, RE-10 |
| `control_verified_date` | Last date the compensating control was tested | RE-10 |
| `remediation_plan` | Plan to remove the need for the exception | RE-11 |
| `remediation_due` | Target date for the plan | RE-11 |
| `renewal_count` | Times the exception has been renewed (blank = 0) | RE-12 |
| `status` | active, pending or closed (blank = active) | Lanes |
| `closed_date` | Date closed | Board |

## People roster (optional)

One row per person who requests, owns or approves exceptions. Start from `samples/people_template.csv`.

| Column | Meaning |
|---|---|
| `name` | Full name, matching the register (case and extra spaces are ignored) |
| `title` | Job title, used for authority if `approval_limit` is blank |
| `approval_limit` | Highest risk level the person may accept: none, low, medium, high or critical |
| `status` | active or left |
| `left_date` | Date the person left (a future date means they have not left yet) |

## Getting the data

Most small organizations keep exceptions in a spreadsheet, a ticketing system (for example a "risk acceptance" request type in Jira or ServiceNow), or a GRC platform. Export those fields to CSV and rename the columns to match the table above. The people roster can come from an HR export or a short list kept by the security team.
