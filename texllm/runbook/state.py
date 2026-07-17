"""Persist runbook phase progress + filled placeholders (shared product state)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from texllm.runbook.catalog import RUNBOOK_PHASES, catalog


class RunbookState:
    def __init__(self, path: Optional[Path] = None) -> None:
        root = Path(".texllm")
        root.mkdir(parents=True, exist_ok=True)
        self.path = path or root / "runbook.json"
        self._data = self._load()

    def _load(self) -> Dict[str, Any]:
        if self.path.is_file():
            try:
                return json.loads(self.path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        phases = {}
        for p in RUNBOOK_PHASES:
            phases[p["id"]] = {
                "status": "ready",
                "placeholder": dict(p.get("placeholder") or {}),
                "result": None,
            }
        return {
            "company_name": "[Your Company]",
            "active_phase": "intent",
            "phases": phases,
        }

    def save(self) -> None:
        self.path.write_text(json.dumps(self._data, indent=2), encoding="utf-8")

    def snapshot(self) -> Dict[str, Any]:
        cat = catalog()
        phases_out = []
        for p in cat["phases"]:
            st = self._data["phases"].get(p["id"], {})
            phases_out.append(
                {
                    **p,
                    "status": st.get("status", p.get("status", "ready")),
                    "placeholder": st.get("placeholder", p.get("placeholder")),
                    "result": st.get("result"),
                }
            )
        done = sum(1 for x in phases_out if x["status"] == "done")
        return {
            **cat,
            "company_name": self._data.get("company_name", "[Your Company]"),
            "active_phase": self._data.get("active_phase", "intent"),
            "phases": phases_out,
            "progress": {
                "done": done,
                "total": len(phases_out),
                "pct": int(100 * done / max(1, len(phases_out))),
            },
        }

    def update_phase(
        self,
        phase_id: str,
        *,
        status: Optional[str] = None,
        placeholder: Optional[Dict[str, Any]] = None,
        result: Any = None,
        company_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        if phase_id not in self._data["phases"]:
            raise KeyError(phase_id)
        ph = self._data["phases"][phase_id]
        if status:
            ph["status"] = status
        if placeholder is not None:
            ph["placeholder"] = placeholder
        if result is not None:
            ph["result"] = result
        if company_name:
            self._data["company_name"] = company_name
        self._data["active_phase"] = phase_id
        self.save()
        return self.snapshot()

    def mark_done(self, phase_id: str, result: Any = None) -> Dict[str, Any]:
        return self.update_phase(phase_id, status="done", result=result)


_runbook: Optional[RunbookState] = None


def get_runbook() -> RunbookState:
    global _runbook
    if _runbook is None:
        _runbook = RunbookState()
    return _runbook
