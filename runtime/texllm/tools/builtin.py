"""Built-in safe tools for sample firmware."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from texllm.tools.registry import ToolRegistry, ToolSpec


def build_builtin_registry() -> ToolRegistry:
    reg = ToolRegistry()

    def echo(text: str) -> Dict[str, Any]:
        return {"echo": text}

    def now() -> Dict[str, Any]:
        return {"utc": datetime.now(timezone.utc).isoformat()}

    def word_count(text: str) -> Dict[str, Any]:
        words = [w for w in text.split() if w]
        return {"words": len(words), "chars": len(text)}

    def checklist(items: list) -> Dict[str, Any]:
        return {
            "items": [{"text": str(i), "done": False} for i in items],
            "count": len(items),
        }

    reg.register(
        ToolSpec(
            name="echo",
            description="Echo text back (debug).",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=echo,
        )
    )
    reg.register(
        ToolSpec(
            name="now",
            description="Return current UTC timestamp.",
            parameters={"type": "object", "properties": {}},
            handler=now,
        )
    )
    reg.register(
        ToolSpec(
            name="word_count",
            description="Count words and characters in text.",
            parameters={
                "type": "object",
                "properties": {"text": {"type": "string"}},
                "required": ["text"],
            },
            handler=word_count,
        )
    )
    reg.register(
        ToolSpec(
            name="checklist",
            description="Turn a list of strings into a checklist structure.",
            parameters={
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {"type": "string"},
                    }
                },
                "required": ["items"],
            },
            handler=checklist,
        )
    )
    return reg
