#!/usr/bin/env python3
"""
T-ex CLI — call from shell or Claude Code as:

  tex teams
  tex dash sales
  tex run sales "Draft outreach for Q3"
  tex review example.com
  tex bd "Find 3 partnership angles"
  tex @T-ex "help with ops incident"

Also: python -m texllm.tex_cli …
"""

from __future__ import annotations

import argparse
import json
import sys


def main(argv: list[str] | None = None) -> int:
    argv = list(argv if argv is not None else sys.argv[1:])

    # Allow: tex @T-ex <prompt...>  or  tex @sales <prompt>
    if argv and argv[0].startswith("@"):
        tag = argv[0][1:]
        prompt = " ".join(argv[1:]).strip()
        if not prompt:
            print("Usage: tex @T-ex <prompt>   or   tex @sales <prompt>", file=sys.stderr)
            return 2
        if tag.lower() in ("t-ex", "tex", "t_ex", "all"):
            return _cmd_run("ceo", prompt, as_json=False)
        return _cmd_run(tag.lower(), prompt, as_json=False)

    parser = argparse.ArgumentParser(
        prog="tex",
        description="T-ex multi-team agent workspace CLI (shared SQLite with web UI)",
    )
    sub = parser.add_subparsers(dest="cmd")

    sub.add_parser("teams", help="List teams")
    sub.add_parser("overview", help="Workspace overview")

    p_dash = sub.add_parser("dash", help="Team dashboard")
    p_dash.add_argument("team", help="Team slug: ops, sales, dev, tech, ceo, fulfillment, personal-bd")

    p_run = sub.add_parser("run", help="Run agentic flow for a team")
    p_run.add_argument("team", help="Team slug")
    p_run.add_argument("goal", nargs="+", help="Goal text")
    p_run.add_argument("--json", action="store_true")
    p_run.add_argument(
        "--code",
        action="store_true",
        help="Code mode: the executor drives a real coding agent (claude CLI) "
        "that edits files in a per-run workdir and returns diff artifacts",
    )
    p_run.add_argument(
        "--workdir",
        default=None,
        help="Code mode only: run in this existing directory instead of an "
        "isolated .texllm/runs/<job-id>/ scratch dir",
    )
    p_run.add_argument(
        "--verify",
        default=None,
        help="Code mode only: done-gate shell command run in the workdir — "
        "the job succeeds ONLY if it exits 0 (e.g. --verify 'pytest -q')",
    )

    p_rev = sub.add_parser("review", help="Domain/website review → ideas, brains, skills")
    p_rev.add_argument("domain", help="example.com or URL")
    p_rev.add_argument("--notes", default="")
    p_rev.add_argument("--json", action="store_true")

    p_bd = sub.add_parser("bd", help="Personal business development agent")
    p_bd.add_argument("goal", nargs="+", help="BD goal")
    p_bd.add_argument("--json", action="store_true")

    p_brain = sub.add_parser("brain", help="Add a brain to a team")
    p_brain.add_argument("team")
    p_brain.add_argument("name")
    p_brain.add_argument("--role", default="specialist")
    p_brain.add_argument("--prompt", default="")

    p_skill = sub.add_parser("skill", help="Add a skill to a team")
    p_skill.add_argument("team")
    p_skill.add_argument("name")
    p_skill.add_argument("--description", default="")
    p_skill.add_argument("--body", default="")

    p_ideas = sub.add_parser("ideas", help="List ideas from domain reviews")
    p_ideas.add_argument("--json", action="store_true")

    p_export = sub.add_parser(
        "export",
        help="Export team brains/skills to firmware/<team>-agents package",
    )
    p_export.add_argument("team", help="Team slug")
    p_export.add_argument("--version", default="0.1.0")
    p_export.add_argument("--json", action="store_true")

    p_card = sub.add_parser("card", help="Add kanban card to team board")
    p_card.add_argument("team")
    p_card.add_argument("title")
    p_card.add_argument("--column", default="backlog")
    p_card.add_argument("--detail", default="")

    sub.add_parser("serve", help="Start host + web (same as texllm serve)")

    p_channels = sub.add_parser(
        "channels", help="Messaging channels: poll workers + status (docs/CHANNELS.md)"
    )
    channels_sub = p_channels.add_subparsers(dest="channels_cmd")
    p_poll = channels_sub.add_parser(
        "poll", help="Run a long-poll worker (no public URL needed)"
    )
    p_poll.add_argument("channel", choices=["telegram"])
    p_poll.add_argument(
        "--once", action="store_true", help="Single getUpdates pass (smoke test)"
    )
    channels_sub.add_parser("list", help="Show configured channel adapters")

    args = parser.parse_args(argv)
    if not args.cmd:
        parser.print_help()
        return 2

    if args.cmd == "teams":
        from texllm.workspace import get_workspace

        for t in get_workspace().list_teams():
            print(f"{t['slug']:16} {t['name']:28} {t.get('description','')[:60]}")
        return 0

    if args.cmd == "overview":
        from texllm.workspace import get_workspace

        print(json.dumps(get_workspace().overview(), indent=2))
        return 0

    if args.cmd == "dash":
        from texllm.workspace import get_workspace

        try:
            print(json.dumps(get_workspace().dashboard(args.team), indent=2))
        except KeyError:
            print(f"Unknown team: {args.team}", file=sys.stderr)
            return 1
        return 0

    if args.cmd == "run":
        return _cmd_run(
            args.team,
            " ".join(args.goal),
            as_json=args.json,
            mode="code" if args.code else "chat",
            workdir=args.workdir,
            verify=args.verify,
        )

    if args.cmd == "review":
        from texllm.workspace.domain_review import review_domain

        out = review_domain(args.domain, notes=args.notes)
        if args.json:
            print(json.dumps(out, indent=2))
        else:
            print(f"domain: {out['domain']}")
            print(f"overview: {out.get('overview')}")
            print(f"ideas: {len(out.get('ideas') or [])}")
            print(f"brains: {len(out.get('brains') or [])}")
            print(f"skills: {len(out.get('skills') or [])}")
            for i in (out.get("ideas") or [])[:8]:
                print(f"  - [{i.get('team_slug')}] {i.get('title')}")
        return 0

    if args.cmd == "bd":
        return _cmd_run("personal-bd", " ".join(args.goal), as_json=args.json)

    if args.cmd == "brain":
        from texllm.workspace import get_workspace

        ws = get_workspace()
        team = ws.get_team(args.team)
        if not team:
            print("Unknown team", file=sys.stderr)
            return 1
        b = ws.add_brain(team["id"], args.name, role=args.role, prompt=args.prompt)
        print(json.dumps(b, indent=2))
        return 0

    if args.cmd == "skill":
        from texllm.workspace import get_workspace

        ws = get_workspace()
        team = ws.get_team(args.team)
        s = ws.add_skill(
            args.name,
            description=args.description,
            body=args.body,
            team_id=team["id"] if team else None,
        )
        print(json.dumps(s, indent=2))
        return 0

    if args.cmd == "ideas":
        from texllm.workspace import get_workspace

        ideas = get_workspace().list_ideas()
        if args.json:
            print(json.dumps(ideas, indent=2))
        else:
            for i in ideas:
                print(f"[{i.get('team_slug')}] {i.get('title')}")
        return 0

    if args.cmd == "export":
        from texllm.workspace.export_firmware import export_team_firmware

        try:
            out = export_team_firmware(args.team, version=args.version)
        except KeyError:
            print(f"Unknown team: {args.team}", file=sys.stderr)
            return 1
        if args.json:
            print(json.dumps(out, indent=2, default=str))
        else:
            print(f"exported: {out['package_id']}@{out['version']}")
            print(f"path: {out['path']}")
            print(
                f"brains: {out['brains_exported']} skills: {out['skills_exported']}"
            )
        return 0

    if args.cmd == "card":
        from texllm.workspace import get_workspace

        ws = get_workspace()
        team = ws.get_team(args.team)
        if not team:
            print("Unknown team", file=sys.stderr)
            return 1
        c = ws.add_kanban_card(
            team["id"], args.title, detail=args.detail, column_key=args.column
        )
        print(json.dumps(c, indent=2))
        return 0

    if args.cmd == "serve":
        from texllm.host.app import main as serve_main

        serve_main()
        return 0

    if args.cmd == "channels":
        return _cmd_channels(args)

    parser.print_help()
    return 2


def _cmd_channels(args) -> int:
    from texllm.channels.service import get_channel_service

    service = get_channel_service()

    if args.channels_cmd == "list" or not args.channels_cmd:
        report = service.status_report()
        if not report["channels"]:
            print(
                "no channels configured — set TELEGRAM_BOT_TOKEN (or WhatsApp/"
                "Google Chat/BlueBubbles/custom env vars) in .env; see docs/CHANNELS.md"
            )
            return 0
        for ch in report["channels"]:
            print(
                f"{ch['name']:12} allowed_senders={ch['allowed_senders']:<3} "
                f"push={str(ch['can_push']).lower():5} sync={str(ch['sync_reply']).lower()}"
            )
        if report.get("default_team"):
            print(f"default team (freeform): {report['default_team']}")
        return 0

    if args.channels_cmd == "poll":
        from texllm.channels.telegram import TelegramAdapter
        from texllm.channels.telegram_poll import TelegramPoller

        adapter = service.adapter("telegram")
        if not isinstance(adapter, TelegramAdapter):
            print(
                "telegram is not configured — set TELEGRAM_BOT_TOKEN in .env",
                file=sys.stderr,
            )
            return 1
        if not adapter.allowed_senders():
            print(
                "WARNING: TELEGRAM_ALLOWED_SENDERS is empty — every message will be "
                "dropped (default-deny). Add your numeric Telegram user id to dispatch.",
                file=sys.stderr,
            )
        poller = TelegramPoller(adapter, service)
        if args.once:
            handled = poller.poll_once()
            print(f"handled {handled} update(s)")
            return 0
        print("telegram long-poll worker running — Ctrl-C to stop")
        try:
            poller.run_forever()
        except KeyboardInterrupt:
            print("stopped")
        return 0

    print("usage: tex channels [list|poll telegram [--once]]", file=sys.stderr)
    return 2


def _cmd_run(
    team: str,
    goal: str,
    *,
    as_json: bool,
    mode: str = "chat",
    workdir: str | None = None,
    verify: str | None = None,
) -> int:
    from texllm.workspace.team_run import run_team_flow

    try:
        out = run_team_flow(team, goal, mode=mode, workdir=workdir, verify=verify)
    except KeyError:
        print(f"Unknown team: {team}", file=sys.stderr)
        return 1
    except Exception as exc:  # noqa: BLE001
        print(str(exc), file=sys.stderr)
        return 1
    if as_json:
        print(json.dumps(out, indent=2, default=str))
    else:
        print(f"team: {out['team']['slug']}")
        print(f"status: {out['status']}")
        if out.get("error"):
            print(f"error: {out['error']}")
        res = out.get("result") or {}
        if res.get("summary"):
            print(f"summary: {res['summary']}")
        output = res.get("output") or {}
        if output.get("mode") == "code":
            print(f"workdir: {output.get('workdir')}")
            if output.get("verify"):
                v = output["verify"]
                print(
                    f"verify: `{v.get('command')}` → exit {v.get('exit_code')} "
                    f"({'PASS' if v.get('ok') else 'FAIL'})"
                )
            files = output.get("files_changed") or []
            print(f"files changed ({len(files)}):")
            for f in files[:50]:
                print(f"  - {f}")
            if output.get("diff"):
                print("diff: (stored in job result; first 40 lines)")
                for line in str(output["diff"]).splitlines()[:40]:
                    print(f"  {line}")
        elif output:
            print("output:")
            print(json.dumps(output, indent=2))
    return 0 if out.get("status") == "succeeded" else 1


if __name__ == "__main__":
    raise SystemExit(main())
