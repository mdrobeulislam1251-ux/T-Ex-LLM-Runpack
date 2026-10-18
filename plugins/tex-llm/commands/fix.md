---
description: Run the issue-fix loop on a bug, error, or incident
---

Run the `issue-fix-loop` skill for: $ARGUMENTS

triage-lead reproduces and classifies severity first. S1 → hotfix-engineer stabilizes
immediately. Otherwise bug-hunter: failing regression test FIRST, then root-cause fix,
then pattern sweep. regression-tester proves it. Systemic or repeat issues go to
root-cause-analyst for class-level prevention.

Loop invariant: a fix without a regression test is not a fix. Report: severity, root
cause, fix, tests added, prevention actions.
