# test_system_core.py
"""Engineering-track manifest gate.

Verifies the App Dev SKILL.md declares the full 65-competency engineering
package and the required Data Security components. Portable: the SKILL.md path
resolves relative to THIS file, so the same test runs under pytest on the
operator workstation and standalone on Linux / the tl-host server (no
hard-coded E:\\ path).

Run:
    pytest "App Dev and Engineering Team/test_system_core.py"
    python3 "App Dev and Engineering Team/test_system_core.py"
"""

import re
from pathlib import Path

# SKILL.md lives in the same directory as this test.
SKILL_MANIFEST_PATH = Path(__file__).resolve().parent / "SKILL.md"


def test_verify_manifest_completeness():
    """Verify that the 65-skill system engineer architecture file is present and completely detailed."""
    # 1. Assert file exists (Fails if Claude skips generating the asset)
    assert SKILL_MANIFEST_PATH.exists() is True, (
        "SKILL.md has not been generated inside the Engineering workspace!"
    )

    content = SKILL_MANIFEST_PATH.read_text(encoding="utf-8")

    # 2. Count distinct skill declarations listed inside the manifest
    skills_found = re.findall(r"\d+\.\s+.*", content)
    print(f"\n[Diagnostic] System detected {len(skills_found)} functional skills defined.")

    # 3. Assert full 65-skill architectural package is active
    assert len(skills_found) >= 65, (
        f"AI Laziness Detected: Core manifest only contains {len(skills_found)} "
        "out of 65 requested competencies."
    )

    # 4. Check for Data Security Package components explicitly
    assert "Row-Level Security" in content, "Data Security Package is missing Database RLS parameters."
    assert "Zero-Trust" in content, "Data Security Package is missing Zero-Trust Architecture parameters."


if __name__ == "__main__":
    test_verify_manifest_completeness()
    print("PASS test_verify_manifest_completeness")
