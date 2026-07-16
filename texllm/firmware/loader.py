"""Load versioned agentic firmware packages from disk."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field


class RoleConfig(BaseModel):
    name: str
    model_tier: str = "default"
    tools: List[str] = Field(default_factory=list)
    prompt_file: str = ""
    temperature: float = 0.2


class FirmwareLimits(BaseModel):
    max_iterations: int = 8
    max_review_retries: int = 2
    max_cost_usd: float = 1.0


class FirmwareManifest(BaseModel):
    id: str
    version: str
    name: str = ""
    description: str = ""
    roles: List[RoleConfig]
    limits: FirmwareLimits = Field(default_factory=FirmwareLimits)
    default_tools: List[str] = Field(default_factory=list)


class FirmwarePackage(BaseModel):
    root: Path
    manifest: FirmwareManifest
    prompts: Dict[str, str] = Field(default_factory=dict)

    model_config = {"arbitrary_types_allowed": True}

    def prompt_for(self, role: str) -> str:
        if role in self.prompts:
            return self.prompts[role]
        cfg = self.role(role)
        if cfg and cfg.prompt_file:
            path = self.root / cfg.prompt_file
            if path.exists():
                return path.read_text(encoding="utf-8")
        return f"You are the {role} role for firmware {self.manifest.id}."

    def role(self, name: str) -> Optional[RoleConfig]:
        for r in self.manifest.roles:
            if r.name == name:
                return r
        return None

    def tools_for(self, role: str) -> List[str]:
        cfg = self.role(role)
        if cfg and cfg.tools:
            return list(cfg.tools)
        return list(self.manifest.default_tools)


def load_firmware(
    firmware_dir: Path,
    firmware_id: str,
    version: str,
) -> FirmwarePackage:
    root = firmware_dir / firmware_id
    if not root.is_dir():
        raise FileNotFoundError(f"Firmware not found: {firmware_id}")

    manifest_path = root / "manifest.yaml"
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest.yaml in {root}")

    raw: Dict[str, Any] = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest = FirmwareManifest.model_validate(raw)
    if manifest.id != firmware_id:
        raise ValueError(f"Manifest id {manifest.id} != requested {firmware_id}")
    if manifest.version != version:
        # Allow directory pin by version folder later; for MVP require match
        raise ValueError(
            f"Manifest version {manifest.version} != requested {version}"
        )

    prompts: Dict[str, str] = {}
    prompts_dir = root / "prompts"
    if prompts_dir.is_dir():
        for p in prompts_dir.glob("*.md"):
            prompts[p.stem] = p.read_text(encoding="utf-8")

    return FirmwarePackage(root=root, manifest=manifest, prompts=prompts)


def list_firmware(firmware_dir: Path) -> List[Dict[str, str]]:
    out: List[Dict[str, str]] = []
    if not firmware_dir.is_dir():
        return out
    for path in sorted(firmware_dir.iterdir()):
        man = path / "manifest.yaml"
        if not man.exists():
            continue
        raw = yaml.safe_load(man.read_text(encoding="utf-8")) or {}
        out.append(
            {
                "id": str(raw.get("id") or path.name),
                "version": str(raw.get("version") or ""),
                "name": str(raw.get("name") or path.name),
            }
        )
    return out
