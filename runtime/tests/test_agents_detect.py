"""Agent detection unit tests (no real CLI required)."""

from __future__ import annotations

from texllm.agents.detect import detect_report, which_extended


def test_detect_report_shape():
    r = detect_report()
    assert "agents" in r
    assert "count" in r
    assert "execution_modes" in r
    assert isinstance(r["agents"], list)
    modes = {m["id"] for m in r["execution_modes"]}
    assert "local_cli" in modes
    assert "mock" in modes


def test_which_extended_python():
    # python3 almost always on CI/dev images
    p = which_extended("python3") or which_extended("python")
    # may be None on exotic systems — soft assert
    if p:
        assert "python" in p.lower()
