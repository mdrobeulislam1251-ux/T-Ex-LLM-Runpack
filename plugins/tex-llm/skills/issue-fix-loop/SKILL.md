---
name: issue-fix-loop
description: The Issue Fixer team's loop — triage, reproduce, fix at root cause, regression-test, and prevent recurrence. Use for every bug report, error, failed test, or production incident.
---

# Issue Fix Loop — Triage → Fix → Prove → Prevent

Every reported problem follows this loop. No step is skippable; the loop is what makes
fixes permanent instead of whack-a-mole.

## 1 — Triage (triage-lead)

- Reproduce first. Not reproducible → request the exact missing info (steps, env,
  logs); do not guess-fix.
- Classify severity:
  - **S1** — production down, data loss/corruption, security breach → hotfix-engineer NOW
  - **S2** — feature broken, no workaround → bug-hunter, this cycle
  - **S3** — broken with workaround → bug-hunter, scheduled
  - **S4** — cosmetic/minor → backlog with notes
- Write the triage record: severity, minimal repro steps, suspected area, assignee.
- Check for duplicates; link, don't double-fix.

## 2a — Emergency path (hotfix-engineer, S1 only)

Stabilize with the smallest safe change: rollback > feature-flag off > minimal patch.
Verify recovery on real dashboards (sre-engineer). Backport to main. Open the real-fix
ticket. Hand the timeline to root-cause-analyst. Stabilization ≠ resolution.

## 2b — Standard path (bug-hunter)

1. Trace to the actual defective logic — debugger, logs, `git bisect`; evidence, not
   hunches.
2. Write the failing regression test FIRST. It must fail for the right reason.
3. Fix the cause. If only a symptom-fix is expedient now, say so explicitly and file
   the cause-fix as a tracked follow-up.
4. Sweep for the same defect pattern elsewhere in the codebase.
5. Commit with the root cause explained in the message.

## 3 — Prove (regression-tester)

- Run the relevant suites; expand scope proportionally to the risk of the change.
- The new regression test joins the permanent suite — every bug that happened once
  becomes impossible to reintroduce silently.
- Report: suites run, pass/fail, tests added, gaps noticed (→ qa-automation-engineer).

## 4 — Prevent (root-cause-analyst, when systemic)

Triggered by: any S1, any bug seen twice, or bug-hunter flagging a systemic smell.

- 5-whys to the process/architecture level: why did the system allow this defect?
- Classify the failure CLASS and propose a defense that kills the class (validation
  layer, type constraint, lint rule, CI check, contract test).
- Route: architectural fixes → cto, process fixes → coo. Log the pattern in
  `.tex-llm/companies/<slug>/incidents.md`.

## Loop invariants

- A fix without a regression test is not a fix.
- "Can't reproduce" is a request for information, never a closure reason by itself.
- Every S1 ends with a blameless postmortem (sre-engineer) within the same working
  session where possible.
- The issue record is updated at every transition; nothing goes silent.
