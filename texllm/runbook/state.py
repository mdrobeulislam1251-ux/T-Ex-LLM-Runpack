"""Persist runbook phase progress + filled placeholders (shared product state)."""

from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path
from typing import Any, Dict, Optional

from texllm.runbook.catalog import RUNBOOK_PHASES, catalog


def _json_default(obj: Any) -> Any:
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):
        return obj.model_dump()
    if hasattr(obj, "dict"):
        return obj.dict()
    return str(obj)


def json_safe(obj: Any) -> Any:
    """Deep-convert to JSON-serializable structure."""
    return json.loads(json.dumps(obj, default=_json_default))


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
            "activity": [],
        }

    def save(self) -> None:
        self.path.write_text(
            json.dumps(self._data, indent=2, default=_json_default),
            encoding="utf-8",
        )

    def log(self, title: str, detail: str = "") -> None:
        act = self._data.setdefault("activity", [])
        act.insert(
            0,
            {
                "title": title,
                "detail": detail,
                "ts": datetime.utcnow().isoformat() + "Z",
            },
        )
        self._data["activity"] = act[:40]
        self.save()

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
            "activity": self._data.get("activity") or [],
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
            ph["placeholder"] = json_safe(placeholder)
        if result is not None:
            ph["result"] = json_safe(result)
        if company_name:
            self._data["company_name"] = company_name
        self._data["active_phase"] = phase_id
        self.save()
        return self.snapshot()


_runbook: Optional[RunbookState] = None


def get_runbook() -> RunbookState:
    global _runbook
    if _runbook is None:
        _runbook = RunbookState()
    return _runbook


def reset_runbook_singleton() -> None:
    global _runbook
    _runbook = None
