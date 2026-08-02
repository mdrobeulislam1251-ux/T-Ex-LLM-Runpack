"""Shared test config: never let the suite touch a real provider.

Provider resolution is Claude-CLI-first (texllm.providers.get_provider), so on any
machine with a `claude` binary the suite would otherwise shell out to it — spending
real tokens where a login works, or failing where the CLI refuses to run (e.g. as
root). TEXLLM_FORCE_MOCK is checked before everything else in get_provider(); set
it for every test so the suite is deterministic and offline on all machines.
"""

from __future__ import annotations

import os

os.environ["TEXLLM_FORCE_MOCK"] = "1"
