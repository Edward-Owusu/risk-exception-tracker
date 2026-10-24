# Risk exception review: Riverbend Components (fictional)

As of 2026-10-24. 11 exceptions in the register, 9 active.

**Governance health: 34/100 (Out of control)**. Accepted risk load: 56.

| Status | Count |
|---|---|
| Expired, still open | 2 |
| Expiring soon | 1 |
| Active | 6 |
| Pending approval | 1 |
| Closed | 1 |

## Findings (21)

| Severity | Exception | Finding | Fix | References |
|---|---|---|---|---|
| critical | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-02 Expired exception still in use: Expired on 2026-02-10 (256 days ago) but is still marked active. | Close the exception and apply the policy, or re-assess the risk and get a new approval with a new expiry date. | NIST RA-7, CA-5; ISO 27001 6.1.3; CSF ID.RA-07 |
| critical | EX-2026-002 No MFA on ERP vendor support account | RE-02 Expired exception still in use: Expired on 2026-10-12 (12 days ago) but is still marked active. | Close the exception and apply the policy, or re-assess the risk and get a new approval with a new expiry date. | NIST RA-7, CA-5; ISO 27001 6.1.3; CSF ID.RA-07 |
| critical | EX-2026-009 PLC network excluded from vulnerability scans | RE-01 Exception in use without a recorded approval: Marked active, but the approver and approval date are missing. | Stop relying on the exception until an authorized approver signs it, or close it and apply the policy. | NIST RA-7, CM-6; ISO 27001 6.1.3; CSF ID.RA-07 |
| high | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-05 Approver lacks authority for this risk level: Alan Ortiz has authority up to high risk (roster), but this exception is critical risk. | Have the exception approved by someone authorized to accept this level of risk. | NIST PM-9, RA-7; ISO 27001 6.1.3; CSF GV.RR-02 |
| high | EX-2025-011 Shared admin account on HMI panels | RE-03 Exception has no expiry date: No expiry date is recorded, so the exception never comes back for review. | Set an expiry date within the maximum allowed for this risk level so the exception is reviewed again. | NIST RA-7, PM-9; ISO 27001 6.1.3; CSF ID.RA-07 |
| high | EX-2025-011 Shared admin account on HMI panels | RE-05 Approver lacks authority for this risk level: Marcus Lee has authority up to medium risk (roster), but this exception is high risk. | Have the exception approved by someone authorized to accept this level of risk. | NIST PM-9, RA-7; ISO 27001 6.1.3; CSF GV.RR-02 |
| high | EX-2025-011 Shared admin account on HMI panels | RE-06 Exception approved by the person who requested it: Marcus Lee both requested and approved this exception. | Have an independent, authorized person review and approve the exception. | NIST AC-5, RA-7; ISO 27001 A.5.3; CSF GV.RR-02 |
| high | EX-2025-011 Shared admin account on HMI panels | RE-09 No compensating control for a high or critical risk: This is high risk, but no compensating control is recorded. | Put a compensating control in place (for example extra monitoring or network isolation) and record it. | NIST RA-7, CA-5; ISO 27001 6.1.3; CSF ID.RA-06 |
| high | EX-2026-007 USB storage allowed in quality lab | RE-07 No current risk owner: Risk owner Lisa Grant left the organization on 2026-06-15. | Assign a current employee as risk owner and have them confirm they accept the risk. | NIST PM-9, RA-7; ISO 27001 6.1.3; CSF GV.RR-02 |
| high | EX-2026-009 PLC network excluded from vulnerability scans | RE-09 No compensating control for a high or critical risk: This is an unrated risk, but no compensating control is recorded. | Put a compensating control in place (for example extra monitoring or network isolation) and record it. | NIST RA-7, CA-5; ISO 27001 6.1.3; CSF ID.RA-06 |
| high | EX-2026-013 Local admin rights on engineering laptops | RE-06 Exception approved by the person who requested it: Priya Raman both requested and approved this exception. | Have an independent, authorized person review and approve the exception. | NIST AC-5, RA-7; ISO 27001 A.5.3; CSF GV.RR-02 |
| medium | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-04 Approved for longer than policy allows: Approved for 365 days; the maximum for critical risk is 90 days. | Shorten the expiry date to the maximum allowed for this risk level, or document why a longer period was approved. | NIST PM-9; ISO 27001 6.1.3; CSF GV.RM-04 |
| medium | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-08 Approver has left the organization: Approver Alan Ortiz left the organization on 2026-03-31. | Have a current authorized approver re-confirm the exception. | NIST PM-9; ISO 27001 6.1.3; CSF ID.RA-07 |
| medium | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-10 Compensating control not verified recently: Compensating control last verified 619 days ago; the limit is 90 days. | Test that the compensating control is working and record the date and evidence. | NIST CA-7; ISO 27001 9.1; CSF ID.RA-06 |
| medium | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-11 No remediation plan, or remediation date passed: Remediation was due on 2026-06-30 and the exception is still open. | Record a plan and a realistic date to remove the need for the exception, and track it to completion. | NIST CA-5; ISO 27001 6.1.3; CSF ID.RA-06 |
| medium | EX-2025-003 Legacy CNC controller runs Windows 7 | RE-12 Exception renewed too many times: Renewed 3 times; the limit is 2. | Treat the exception as a permanent risk: escalate it, fund the fix, or formally update the policy. | NIST PM-9, CA-5; ISO 27001 6.1.3; CSF ID.RA-07 |
| medium | EX-2025-011 Shared admin account on HMI panels | RE-11 No remediation plan, or remediation date passed: No plan is recorded to remove the need for this exception. | Record a plan and a realistic date to remove the need for the exception, and track it to completion. | NIST CA-5; ISO 27001 6.1.3; CSF ID.RA-06 |
| medium | EX-2026-007 USB storage allowed in quality lab | RE-11 No remediation plan, or remediation date passed: No plan is recorded to remove the need for this exception. | Record a plan and a realistic date to remove the need for the exception, and track it to completion. | NIST CA-5; ISO 27001 6.1.3; CSF ID.RA-06 |
| medium | EX-2026-013 Local admin rights on engineering laptops | RE-04 Approved for longer than policy allows: Approved for 365 days; the maximum for high risk is 180 days. | Shorten the expiry date to the maximum allowed for this risk level, or document why a longer period was approved. | NIST PM-9; ISO 27001 6.1.3; CSF GV.RM-04 |
| medium | EX-2026-013 Local admin rights on engineering laptops | RE-10 Compensating control not verified recently: A compensating control is recorded but there is no date showing it was ever verified. | Test that the compensating control is working and record the date and evidence. | NIST CA-7; ISO 27001 9.1; CSF ID.RA-06 |
| low | EX-2026-006 8-character password minimum on kiosks | RE-13 Exception expires soon: Expires on 2026-11-10, in 17 days. | Decide now whether to close, fix, or renew the exception, so it does not lapse while still in use. | NIST RA-7; ISO 27001 6.1.3; CSF ID.RA-07 |

## Risk owners

| Risk owner | Active | Risk load | Expired | Findings |
|---|---|---|---|---|
| Marcus Lee | 3 | 18 | 0 | 7 |
| Priya Raman | 2 | 16 | 0 | 3 |
| Tom Becker | 2 | 13 | 1 | 8 |
| Jordan Price | 1 | 6 | 1 | 1 |
| Lisa Grant | 1 | 3 | 0 | 2 |

## Register

| ID | Exception | Risk | Owner | Expires | Status | Governance |
|---|---|---|---|---|---|---|
| EX-2025-003 | Legacy CNC controller runs Windows 7 | critical | Tom Becker | 2026-02-10 | Expired, still open | Out of control |
| EX-2026-002 | No MFA on ERP vendor support account | high | Jordan Price | 2026-10-12 | Expired, still open | Out of control |
| EX-2026-006 | 8-character password minimum on kiosks | medium | Tom Becker | 2026-11-10 | Expiring soon | Well governed |
| EX-2026-009 | PLC network excluded from vulnerability scans | unrated | Marcus Lee | 2027-03-01 | Active | Out of control |
| EX-2026-007 | USB storage allowed in quality lab | medium | Lisa Grant | 2027-01-20 | Active | Weak |
| EX-2026-013 | Local admin rights on engineering laptops | high | Priya Raman | 2027-07-01 | Active | Weak |
| EX-2025-011 | Shared admin account on HMI panels | high | Marcus Lee | none | Active | Weak |
| EX-2026-010 | Firewall rule allows RDP from vendor IP | critical | Priya Raman | 2026-11-30 | Active | Well governed |
| EX-2026-004 | File server backups use domain admin credentials | high | Marcus Lee | 2027-01-28 | Active | Well governed |
| EX-2026-012 | Sales mailbox retention below policy | low | Jordan Price | none | Pending approval | Not checked |
| EX-2025-001 | Antivirus disabled on barcode scanners | medium | Tom Becker | 2026-05-01 | Closed | Not checked |

_Generated by risk-exception-tracker 0.1.0._
