"""Typed tool registry with allowlists."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: Dict[str, Any]
    handler: Callable[..., Any]
    side_effect: bool = False


@dataclass
class ToolRegistry:
    tools: Dict[str, ToolSpec] = field(default_factory=dict)

    def register(self, spec: ToolSpec) -> None:
        self.tools[spec.name] = spec

    def allowlist(self, names: List[str]) -> "ToolRegistry":
        allowed = {n: self.tools[n] for n in names if n in self.tools}
        return ToolRegistry(tools=allowed)

    def list_public(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": t.name,
                "description": t.description,
                "parameters": t.parameters,
                "side_effect": t.side_effect,
            }
            for t in self.tools.values()
        ]

    def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        if name not in self.tools:
            raise KeyError(f"Tool not allowed or unknown: {name}")
        args = arguments or {}
        if not isinstance(args, dict):
            raise TypeError("Tool arguments must be an object")
        return self.tools[name].handler(**args)

    def describe_for_prompt(self) -> str:
        return json.dumps(self.list_public(), indent=2)
