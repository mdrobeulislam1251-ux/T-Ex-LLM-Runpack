"""Chat command grammar — the security-relevant edge of the chat surface.

    run <team> [--code] <goal...>   dispatch a team run (code = real file edits)
    status <job-id-prefix>          one job's state
    teams                           list workspace teams
    jobs                            last few jobs
    help                            this text
    <anything else>                 freeform → draft run on the default team

Pure function, no I/O. Team existence is the service's job; this only parses.
`--workdir` is deliberately NOT accepted from chat: a remote sender must never
point code-mode at an arbitrary host path — runs stay in the isolated
.texllm/runs/<job-id>/ scratch dir. Use the tex CLI for in-place work.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VERBS = {"run", "status", "teams", "jobs", "help"}

_MENTION = re.compile(r"^@\S+\s+")

USAGE_RUN = "usage: run <team> [--code] <goal>"
USAGE_STATUS = "usage: status <job-id-prefix>"


class CommandError(Exception):
    """User-facing usage error — str(exc) is the chat reply."""


@dataclass
class ParsedCommand:
    kind: str  # "run" | "status" | "teams" | "jobs" | "help" | "freeform"
    team: str = ""
    goal: str = ""
    code: bool = False
    arg: str = ""


def parse_command(text: str) -> ParsedCommand:
    original = (text or "").strip()
    stripped = _MENTION.sub("", original, count=1)

    tokens = stripped.split()
    if not tokens:
        return ParsedCommand(kind="freeform", goal="")

    first = tokens[0]
    if first.startswith("/"):
        first = first[1:]
    verb = first.lower()

    if verb not in VERBS:
        return ParsedCommand(kind="freeform", goal=stripped)

    if verb == "run":
        rest = tokens[1:]
        if not rest:
            raise CommandError(USAGE_RUN)
        team = rest[0].lower()
        args = rest[1:]

        code = False
        goal_tokens = []
        for tok in args:
            if tok == "--code":
                code = True
                continue
            if tok == "--workdir" or tok.startswith("--workdir="):
                raise CommandError(
                    "workdir is not available from chat — run it from the tex CLI "
                    "(chat code runs use an isolated .texllm/runs/<job-id>/ dir)"
                )
            goal_tokens.append(tok)

        goal = " ".join(goal_tokens)
        if not goal:
            raise CommandError(USAGE_RUN)
        return ParsedCommand(kind="run", team=team, goal=goal, code=code)

    if verb == "status":
        if len(tokens) < 2:
            raise CommandError(USAGE_STATUS)
        return ParsedCommand(kind="status", arg=tokens[1])

    return ParsedCommand(kind=verb)


HELP_TEXT = (
    "T-Ex commands:\n"
    "run <team> [--code] <goal> — dispatch a run (--code = real file edits + diff)\n"
    "status <job-id-prefix> — job state\n"
    "teams — list teams\n"
    "jobs — recent jobs\n"
    "help — this text\n"
    "Anything else is sent to the default team as a draft run (if configured)."
)
