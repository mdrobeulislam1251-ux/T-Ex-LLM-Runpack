"""Command grammar + adapter-contract primitives for messaging channels.

Pure unit tests — no I/O, no provider. The parser is the security-relevant edge
of the chat surface (it decides what can trigger a run), so every rule is pinned:
verb casing, --code anywhere, --workdir rejected, mention/slash stripping,
freeform fallback, goal case preserved.
"""

from __future__ import annotations

import os

import pytest

os.environ["TEXLLM_FORCE_MOCK"] = "1"

from texllm.channels.base import parse_senders
from texllm.channels.commands import CommandError, parse_command


# ----- run verb -----

def test_run_basic():
    cmd = parse_command("run dev Ship the release notes")
    assert cmd.kind == "run"
    assert cmd.team == "dev"
    assert cmd.goal == "Ship the release notes"
    assert cmd.code is False


def test_run_code_flag_before_goal():
    cmd = parse_command("run dev --code Add a healthz endpoint")
    assert cmd.kind == "run"
    assert cmd.code is True
    assert cmd.goal == "Add a healthz endpoint"


def test_run_code_flag_after_goal():
    cmd = parse_command("run dev Add a healthz endpoint --code")
    assert cmd.code is True
    assert cmd.goal == "Add a healthz endpoint"


def test_run_team_lowercased_goal_case_preserved():
    cmd = parse_command("run DEV Fix THE Parser")
    assert cmd.team == "dev"
    assert cmd.goal == "Fix THE Parser"


def test_run_workdir_rejected():
    with pytest.raises(CommandError) as exc:
        parse_command("run dev --workdir /tmp fix the thing")
    assert "workdir" in str(exc.value).lower()


def test_run_workdir_equals_rejected():
    with pytest.raises(CommandError):
        parse_command("run dev --workdir=/tmp fix it")


def test_run_missing_goal():
    with pytest.raises(CommandError) as exc:
        parse_command("run dev")
    assert "usage" in str(exc.value).lower()


def test_run_missing_team_and_goal():
    with pytest.raises(CommandError):
        parse_command("run")


# ----- mention / slash prefixes -----

def test_leading_slash_verb():
    assert parse_command("/run dev x y").kind == "run"
    assert parse_command("/help").kind == "help"


def test_leading_mention_stripped():
    cmd = parse_command("@TexBot run dev Ship it")
    assert cmd.kind == "run"
    assert cmd.team == "dev"
    assert cmd.goal == "Ship it"


def test_mention_then_slash():
    assert parse_command("@bot /teams").kind == "teams"


# ----- other verbs -----

def test_status_with_arg():
    cmd = parse_command("status abc12345")
    assert cmd.kind == "status"
    assert cmd.arg == "abc12345"


def test_status_without_arg():
    with pytest.raises(CommandError):
        parse_command("status")


def test_teams_jobs_help_case_insensitive():
    assert parse_command("TEAMS").kind == "teams"
    assert parse_command("Jobs extra tokens ignored").kind == "jobs"
    assert parse_command("help").kind == "help"


# ----- freeform fallback -----

def test_freeform_preserved():
    cmd = parse_command("what should the CEO prioritize this week?")
    assert cmd.kind == "freeform"
    assert cmd.goal == "what should the CEO prioritize this week?"


def test_empty_text_is_freeform_empty():
    cmd = parse_command("   ")
    assert cmd.kind == "freeform"
    assert cmd.goal == ""


# ----- allowlist parsing (base.py) -----

def test_parse_senders_normalizes():
    got = parse_senders(" 42, 43 ,, ABC ,")
    assert got == frozenset({"42", "43", "abc"})


def test_parse_senders_empty():
    assert parse_senders("") == frozenset()
    assert parse_senders(" , ,") == frozenset()
