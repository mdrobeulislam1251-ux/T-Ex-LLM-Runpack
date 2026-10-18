"""Adapter registry — how built-in and third-party channels become available.

Third-party flow: write a module that subclasses ChannelAdapter and calls
register_adapter(MyAdapter) at import time, then set
CHANNEL_PLUGINS=your.module[,another.module] — build_adapters imports the
modules, so registration happens with zero core-file edits.
"""

from __future__ import annotations

import importlib
import logging
from typing import Dict, List, Type

from texllm.channels.base import ChannelAdapter
from texllm.config import Settings

logger = logging.getLogger(__name__)

_REGISTRY: Dict[str, Type[ChannelAdapter]] = {}


def register_adapter(cls: Type[ChannelAdapter]) -> Type[ChannelAdapter]:
    if not cls.name:
        raise ValueError(f"{cls.__name__} must set a class-level name")
    _REGISTRY[cls.name] = cls
    return cls


def registered_names() -> List[str]:
    return sorted(_REGISTRY)


def build_adapters(settings: Settings) -> Dict[str, ChannelAdapter]:
    """Instantiate every registered adapter whose env config is present."""
    for mod in (settings.channel_plugins or "").split(","):
        mod = mod.strip()
        if not mod:
            continue
        try:
            importlib.import_module(mod)
        except Exception:  # noqa: BLE001 — a broken plugin never blocks the host
            logger.warning("channel plugin import failed: %s", mod, exc_info=True)

    adapters: Dict[str, ChannelAdapter] = {}
    for name, cls in list(_REGISTRY.items()):
        try:
            instance = cls.from_settings(settings)
        except Exception:  # noqa: BLE001
            logger.warning("adapter %s from_settings failed", name, exc_info=True)
            instance = None
        if instance is not None:
            adapters[name] = instance
    return adapters
