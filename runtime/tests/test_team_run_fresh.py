"""Fresh-project regression: the FIRST team run must work outside the runtime checkout.

`firmware_dir` is CWD-relative and `sample-assistant` only ships inside the runtime
repo, so in a brand-new project directory the first `tex run <team>` used to fail with
"Firmware not found: sample-assistant" until the user manually ran `tex export`.
"""

from __future__ import annotations

import os
from pathlib import Path

os.environ["TEXLLM_FORCE_MOCK"] = "1"


def test_first_run_in_fresh_project_dir_autoexports_firmware(
    tmp_path: Path, monkeypatch
):
    monkeypatch.chdir(tmp_path)  # like a user project dir: no firmware/ anywhere
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.team_run import run_team_flow

    db = WorkspaceDB()  # seeds .texllm/workspace.db in the fresh dir

    out = run_team_flow("dev", "Design the invoicing API", db=db)

    assert out["status"] == "succeeded", f"first run failed: {out['error']}"
    assert (tmp_path / "firmware" / "dev-agents" / "manifest.yaml").is_file()
    assert out["result"]["review_passed"] is True


def test_existing_export_still_preferred(tmp_path: Path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    from texllm.workspace.db import WorkspaceDB
    from texllm.workspace.export_firmware import export_team_firmware
    from texllm.workspace.team_run import run_team_flow

    db = WorkspaceDB()
    exported = export_team_firmware("sales", db=db)
    manifest = Path(exported["path"]) / "manifest.yaml"
    before = manifest.read_text(encoding="utf-8")

    out = run_team_flow("sales", "Weekly pipeline review", db=db)

    assert out["status"] == "succeeded", out["error"]
    # A pre-existing package is used as-is, not regenerated
    assert manifest.read_text(encoding="utf-8") == before
