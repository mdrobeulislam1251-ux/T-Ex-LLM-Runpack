"""TDD gate for Arion SKILL.md loading.

Ensures Arion can locate and read each track's SKILL.md and that every
Intent Hook a skill declares points at a folder that actually exists — so
Arion cannot hallucinate a route to a directory that isn't there.

Portability: paths resolve relative to THIS file's directory (the repo
root), so the identical test passes on Windows, Linux, and the tl-host
server. No hard-coded absolute paths.

Run:
    pytest core_router_test.py          # on your workstation
    python3 core_router_test.py         # zero-dependency fallback
"""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent
WORKSPACE_SKILL = REPO_ROOT / "Robeul's Workspace Assistant" / "SKILL.md"
APPDEV_SKILL = REPO_ROOT / "App Dev and Engineering Team" / "SKILL.md"

# Matches a route target in an Intent Hook line, e.g. `-> Route to: .\gmail\`
_ROUTE_RE = re.compile(r"Route to:\s*`?\.?[\\/]?([A-Za-z0-9_./\\-]+?)[\\/]?`?\s*$")


def test_arion_skill_loading():
    """Arion can look up and read the Workspace SKILL.md parameters."""
    # Force failure if the skill file doesn't exist yet.
    assert WORKSPACE_SKILL.exists(), f"missing skill file: {WORKSPACE_SKILL}"

    content = WORKSPACE_SKILL.read_text(encoding="utf-8")
    # Ensure keyword hooks are explicitly declared.
    assert "# Intent Hooks" in content


def test_appdev_skill_loading():
    """The engineering track also declares a readable SKILL.md."""
    assert APPDEV_SKILL.exists(), f"missing skill file: {APPDEV_SKILL}"
    content = APPDEV_SKILL.read_text(encoding="utf-8")
    assert "# Execution Rules" in content


def test_intent_hook_targets_exist_on_disk():
    """Every `Route to:` target declared in the Workspace skill must be a
    real folder — this is the anti-hallucination guard."""
    content = WORKSPACE_SKILL.read_text(encoding="utf-8")
    track_dir = WORKSPACE_SKILL.parent

    targets = []
    for line in content.splitlines():
        if "Route to:" not in line:
            continue
        match = _ROUTE_RE.search(line.strip())
        assert match, f"could not parse route target from: {line!r}"
        targets.append(match.group(1).replace("\\", "/"))

    assert targets, "no Intent Hook routes declared"
    for target in targets:
        resolved = (track_dir / target).resolve()
        assert resolved.is_dir(), f"declared route target does not exist: {target}"


def _run_standalone() -> int:
    tests = [
        test_arion_skill_loading,
        test_appdev_skill_loading,
        test_intent_hook_targets_exist_on_disk,
    ]
    failures = 0
    for test in tests:
        try:
            test()
        except AssertionError as exc:
            failures += 1
            print(f"FAIL {test.__name__}: {exc}")
        else:
            print(f"PASS {test.__name__}")
    print(f"\n{len(tests) - failures}/{len(tests)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(_run_standalone())
