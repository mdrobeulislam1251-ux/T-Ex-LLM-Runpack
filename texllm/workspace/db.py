"""Shared SQLite backend for web UI + CLI (single source of truth)."""

from __future__ import annotations

import json
import sqlite3
import threading
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional


def _utcnow() -> str:
    return datetime.now(timezone.utc).isoformat()


def _id() -> str:
    return str(uuid.uuid4())


DEFAULT_TEAMS = [
    {
        "slug": "ops",
        "name": "Operations",
        "kind": "ops",
        "description": "Runbooks, SLAs, incidents, capacity",
        "color": "#2563eb",
    },
    {
        "slug": "sales",
        "name": "Sales",
        "kind": "sales",
        "description": "Pipeline, outreach, proposals, CRM notes",
        "color": "#059669",
    },
    {
        "slug": "dev",
        "name": "Engineering",
        "kind": "dev",
        "description": "Build, ship, review, technical delivery",
        "color": "#7c3aed",
    },
    {
        "slug": "tech",
        "name": "Tech / Platform",
        "kind": "tech",
        "description": "Architecture, infra, reliability",
        "color": "#0891b2",
    },
    {
        "slug": "ceo",
        "name": "CEO / Exec",
        "kind": "ceo",
        "description": "Strategy, KPIs, board narrative, priorities",
        "color": "#b45309",
    },
    {
        "slug": "fulfillment",
        "name": "Fulfillment",
        "kind": "fulfillment",
        "description": "Orders, delivery, customer handoff",
        "color": "#db2777",
    },
    {
        "slug": "personal-bd",
        "name": "Personal Business Development",
        "kind": "personal_bd",
        "description": "Your personal BD agent: pipeline, partnerships, growth",
        "color": "#4f46e5",
    },
]


class WorkspaceDB:
    def __init__(self, path: Optional[Path] = None) -> None:
        root = Path(".texllm")
        root.mkdir(parents=True, exist_ok=True)
        self.path = path or root / "workspace.db"
        self._lock = threading.Lock()
        self._init()

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(str(self.path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def _init(self) -> None:
        with self._lock, self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS teams (
                  id TEXT PRIMARY KEY,
                  slug TEXT UNIQUE NOT NULL,
                  name TEXT NOT NULL,
                  kind TEXT NOT NULL,
                  description TEXT DEFAULT '',
                  color TEXT DEFAULT '#2563eb',
                  active INTEGER DEFAULT 1,
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS brains (
                  id TEXT PRIMARY KEY,
                  team_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  role TEXT DEFAULT 'specialist',
                  prompt TEXT DEFAULT '',
                  model_tier TEXT DEFAULT 'default',
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(team_id) REFERENCES teams(id)
                );
                CREATE TABLE IF NOT EXISTS skills (
                  id TEXT PRIMARY KEY,
                  team_id TEXT,
                  name TEXT NOT NULL,
                  path TEXT DEFAULT '',
                  description TEXT DEFAULT '',
                  body TEXT DEFAULT '',
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS ideas (
                  id TEXT PRIMARY KEY,
                  source TEXT DEFAULT 'domain_review',
                  domain TEXT DEFAULT '',
                  url TEXT DEFAULT '',
                  title TEXT NOT NULL,
                  summary TEXT DEFAULT '',
                  team_slug TEXT DEFAULT '',
                  status TEXT DEFAULT 'new',
                  payload TEXT DEFAULT '{}',
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS flows (
                  id TEXT PRIMARY KEY,
                  team_id TEXT NOT NULL,
                  name TEXT NOT NULL,
                  steps TEXT DEFAULT '[]',
                  status TEXT DEFAULT 'idle',
                  last_run_at TEXT,
                  created_at TEXT NOT NULL,
                  FOREIGN KEY(team_id) REFERENCES teams(id)
                );
                CREATE TABLE IF NOT EXISTS activities (
                  id TEXT PRIMARY KEY,
                  team_id TEXT,
                  kind TEXT NOT NULL,
                  title TEXT NOT NULL,
                  detail TEXT DEFAULT '',
                  created_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS workspace_meta (
                  key TEXT PRIMARY KEY,
                  value TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kpis (
                  id TEXT PRIMARY KEY,
                  team_id TEXT NOT NULL,
                  label TEXT NOT NULL,
                  value TEXT DEFAULT '0',
                  unit TEXT DEFAULT '',
                  trend TEXT DEFAULT 'flat',
                  target TEXT DEFAULT '',
                  sort_order INTEGER DEFAULT 0,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(team_id) REFERENCES teams(id)
                );
                CREATE TABLE IF NOT EXISTS kanban_cards (
                  id TEXT PRIMARY KEY,
                  team_id TEXT NOT NULL,
                  title TEXT NOT NULL,
                  detail TEXT DEFAULT '',
                  column_key TEXT DEFAULT 'backlog',
                  priority TEXT DEFAULT 'med',
                  assignee TEXT DEFAULT '',
                  sort_order INTEGER DEFAULT 0,
                  created_at TEXT NOT NULL,
                  updated_at TEXT NOT NULL,
                  FOREIGN KEY(team_id) REFERENCES teams(id)
                );
                """
            )
            n = conn.execute("SELECT COUNT(*) AS c FROM teams").fetchone()["c"]
            if n == 0:
                for t in DEFAULT_TEAMS:
                    tid = _id()
                    conn.execute(
                        "INSERT INTO teams (id, slug, name, kind, description, color, active, created_at) "
                        "VALUES (?,?,?,?,?,?,1,?)",
                        (
                            tid,
                            t["slug"],
                            t["name"],
                            t["kind"],
                            t["description"],
                            t["color"],
                            _utcnow(),
                        ),
                    )
                    # default brain + flow per team
                    conn.execute(
                        "INSERT INTO brains (id, team_id, name, role, prompt, model_tier, created_at) "
                        "VALUES (?,?,?,?,?,?,?)",
                        (
                            _id(),
                            tid,
                            f"{t['name']} Lead",
                            "lead",
                            f"You are the lead agent for the {t['name']} team. Focus: {t['description']}",
                            "default",
                            _utcnow(),
                        ),
                    )
                    steps = json.dumps(
                        [
                            {"role": "planner", "label": "Plan"},
                            {"role": "executor", "label": "Execute"},
                            {"role": "reviewer", "label": "Review"},
                        ]
                    )
                    conn.execute(
                        "INSERT INTO flows (id, team_id, name, steps, status, created_at) "
                        "VALUES (?,?,?,?, 'idle', ?)",
                        (
                            _id(),
                            tid,
                            f"{t['name']} default flow",
                            steps,
                            _utcnow(),
                        ),
                    )
                    self._seed_team_board(conn, tid, t["kind"], t["name"])
                conn.execute(
                    "INSERT OR REPLACE INTO workspace_meta (key, value) VALUES (?,?)",
                    ("name", "T-ex Agent Workspace"),
                )
            else:
                # migrate existing teams missing kpis/kanban
                for row in conn.execute("SELECT id, kind, name FROM teams").fetchall():
                    kc = conn.execute(
                        "SELECT COUNT(*) AS c FROM kpis WHERE team_id=?",
                        (row["id"],),
                    ).fetchone()["c"]
                    if kc == 0:
                        self._seed_team_board(
                            conn, row["id"], row["kind"], row["name"]
                        )

    def _seed_team_board(
        self, conn: sqlite3.Connection, team_id: str, kind: str, name: str
    ) -> None:
        now = _utcnow()
        kpi_sets = {
            "ops": [
                ("Open incidents", "3", "", "down"),
                ("SLA met", "97", "%", "up"),
                ("MTTR", "42", "min", "down"),
                ("Runbooks", "18", "", "up"),
            ],
            "sales": [
                ("Pipeline", "128", "k", "up"),
                ("Win rate", "24", "%", "up"),
                ("Open deals", "14", "", "flat"),
                ("Avg cycle", "21", "d", "down"),
            ],
            "dev": [
                ("PRs open", "9", "", "flat"),
                ("Deploy/week", "12", "", "up"),
                ("CI green", "94", "%", "up"),
                ("Bugs", "7", "", "down"),
            ],
            "tech": [
                ("Uptime", "99.9", "%", "up"),
                ("p95 latency", "180", "ms", "down"),
                ("Services", "22", "", "up"),
                ("Debt items", "11", "", "down"),
            ],
            "ceo": [
                ("ARR", "1.2", "M", "up"),
                ("NPS", "48", "", "up"),
                ("Priorities", "5", "", "flat"),
                ("Burn", "82", "k", "flat"),
            ],
            "fulfillment": [
                ("Orders/day", "340", "", "up"),
                ("On-time", "96", "%", "up"),
                ("Backlog", "28", "", "down"),
                ("Returns", "2.1", "%", "down"),
            ],
            "personal_bd": [
                ("Leads", "16", "", "up"),
                ("Intros", "4", "", "up"),
                ("Warm", "7", "", "flat"),
                ("Closed", "1", "", "up"),
            ],
        }
        kpis = kpi_sets.get(kind) or [
            ("Active agents", "1", "", "up"),
            ("Flows", "1", "", "flat"),
            ("Ideas", "0", "", "flat"),
            ("Skills", "0", "", "flat"),
        ]
        for i, (label, value, unit, trend) in enumerate(kpis):
            conn.execute(
                "INSERT INTO kpis (id, team_id, label, value, unit, trend, target, sort_order, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?)",
                (_id(), team_id, label, value, unit, trend, "", i, now),
            )
        cards = [
            ("backlog", f"Review {name} priorities", "med"),
            ("todo", "Connect Claude auth for real runs", "high"),
            ("doing", f"Active agent flow for {name}", "med"),
            ("review", "Validate last agent output", "med"),
            ("done", "Team workspace seeded", "low"),
        ]
        for i, (col, title, pri) in enumerate(cards):
            conn.execute(
                "INSERT INTO kanban_cards (id, team_id, title, detail, column_key, priority, assignee, sort_order, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    _id(),
                    team_id,
                    title,
                    "",
                    col,
                    pri,
                    "agent",
                    i,
                    now,
                    now,
                ),
            )

    # --- teams ---
    def list_teams(self) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM teams WHERE active=1 ORDER BY name"
            ).fetchall()
            return [dict(r) for r in rows]

    def get_team(self, slug: str) -> Optional[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM teams WHERE slug=? OR id=?", (slug, slug)
            ).fetchone()
            return dict(row) if row else None

    def create_team(
        self,
        *,
        slug: str,
        name: str,
        kind: str = "custom",
        description: str = "",
        color: str = "#64748b",
    ) -> Dict[str, Any]:
        tid = _id()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO teams (id, slug, name, kind, description, color, active, created_at) "
                "VALUES (?,?,?,?,?,?,1,?)",
                (tid, slug, name, kind, description, color, _utcnow()),
            )
            conn.execute(
                "INSERT INTO brains (id, team_id, name, role, prompt, model_tier, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (
                    _id(),
                    tid,
                    f"{name} Lead",
                    "lead",
                    f"You are the lead agent for {name}. {description}",
                    "default",
                    _utcnow(),
                ),
            )
            conn.execute(
                "INSERT INTO flows (id, team_id, name, steps, status, created_at) VALUES (?,?,?,?, 'idle', ?)",
                (
                    _id(),
                    tid,
                    f"{name} default flow",
                    json.dumps(
                        [
                            {"role": "planner", "label": "Plan"},
                            {"role": "executor", "label": "Execute"},
                            {"role": "reviewer", "label": "Review"},
                        ]
                    ),
                    _utcnow(),
                ),
            )
            self._seed_team_board(conn, tid, kind, name)
        team = self.get_team(slug)
        assert team
        self.log_activity(team["id"], "team_created", f"Team {name} created", description)
        return team

    # --- brains / skills ---
    def list_brains(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            if team_id:
                rows = conn.execute(
                    "SELECT * FROM brains WHERE team_id=? ORDER BY name", (team_id,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM brains ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def add_brain(
        self,
        team_id: str,
        name: str,
        role: str = "specialist",
        prompt: str = "",
        model_tier: str = "default",
    ) -> Dict[str, Any]:
        bid = _id()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO brains (id, team_id, name, role, prompt, model_tier, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (bid, team_id, name, role, prompt, model_tier, _utcnow()),
            )
            row = conn.execute("SELECT * FROM brains WHERE id=?", (bid,)).fetchone()
        self.log_activity(team_id, "brain_added", f"Brain {name}", role)
        return dict(row)

    def list_skills(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            if team_id:
                rows = conn.execute(
                    "SELECT * FROM skills WHERE team_id=? OR team_id IS NULL ORDER BY name",
                    (team_id,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM skills ORDER BY name").fetchall()
            return [dict(r) for r in rows]

    def add_skill(
        self,
        name: str,
        description: str = "",
        body: str = "",
        path: str = "",
        team_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        sid = _id()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO skills (id, team_id, name, path, description, body, created_at) "
                "VALUES (?,?,?,?,?,?,?)",
                (sid, team_id, name, path, description, body, _utcnow()),
            )
            row = conn.execute("SELECT * FROM skills WHERE id=?", (sid,)).fetchone()
        self.log_activity(team_id, "skill_added", f"Skill {name}", description)
        return dict(row)

    # --- ideas / domain review ---
    def add_idea(
        self,
        title: str,
        summary: str = "",
        domain: str = "",
        url: str = "",
        team_slug: str = "",
        payload: Optional[Dict[str, Any]] = None,
        source: str = "domain_review",
    ) -> Dict[str, Any]:
        iid = _id()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO ideas (id, source, domain, url, title, summary, team_slug, status, payload, created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    iid,
                    source,
                    domain,
                    url,
                    title,
                    summary,
                    team_slug,
                    "new",
                    json.dumps(payload or {}),
                    _utcnow(),
                ),
            )
            row = conn.execute("SELECT * FROM ideas WHERE id=?", (iid,)).fetchone()
        return dict(row)

    def list_ideas(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM ideas ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["payload"] = json.loads(d.get("payload") or "{}")
                except json.JSONDecodeError:
                    d["payload"] = {}
                out.append(d)
            return out

    # --- flows / activity ---
    def list_flows(self, team_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM flows WHERE team_id=? ORDER BY name", (team_id,)
            ).fetchall()
            out = []
            for r in rows:
                d = dict(r)
                try:
                    d["steps"] = json.loads(d.get("steps") or "[]")
                except json.JSONDecodeError:
                    d["steps"] = []
                out.append(d)
            return out

    def log_activity(
        self,
        team_id: Optional[str],
        kind: str,
        title: str,
        detail: str = "",
    ) -> None:
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO activities (id, team_id, kind, title, detail, created_at) "
                "VALUES (?,?,?,?,?,?)",
                (_id(), team_id, kind, title, detail, _utcnow()),
            )

    def list_activities(
        self, team_id: Optional[str] = None, limit: int = 40
    ) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            if team_id:
                rows = conn.execute(
                    "SELECT * FROM activities WHERE team_id=? ORDER BY created_at DESC LIMIT ?",
                    (team_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM activities ORDER BY created_at DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(r) for r in rows]

    # --- KPIs ---
    def list_kpis(self, team_id: str) -> List[Dict[str, Any]]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM kpis WHERE team_id=? ORDER BY sort_order, label",
                (team_id,),
            ).fetchall()
            return [dict(r) for r in rows]

    def update_kpi(
        self,
        kpi_id: str,
        *,
        value: Optional[str] = None,
        trend: Optional[str] = None,
        target: Optional[str] = None,
        label: Optional[str] = None,
    ) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            row = conn.execute("SELECT * FROM kpis WHERE id=?", (kpi_id,)).fetchone()
            if not row:
                raise KeyError(kpi_id)
            d = dict(row)
            conn.execute(
                "UPDATE kpis SET value=?, trend=?, target=?, label=?, updated_at=? WHERE id=?",
                (
                    value if value is not None else d["value"],
                    trend if trend is not None else d["trend"],
                    target if target is not None else d["target"],
                    label if label is not None else d["label"],
                    _utcnow(),
                    kpi_id,
                ),
            )
            row = conn.execute("SELECT * FROM kpis WHERE id=?", (kpi_id,)).fetchone()
            return dict(row)

    # --- Kanban ---
    KANBAN_COLUMNS = [
        {"key": "backlog", "label": "Backlog"},
        {"key": "todo", "label": "To do"},
        {"key": "doing", "label": "Doing"},
        {"key": "review", "label": "Review"},
        {"key": "done", "label": "Done"},
    ]

    def list_kanban(self, team_id: str) -> Dict[str, Any]:
        with self._lock, self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM kanban_cards WHERE team_id=? ORDER BY sort_order, updated_at DESC",
                (team_id,),
            ).fetchall()
            cards = [dict(r) for r in rows]
        columns = []
        for col in self.KANBAN_COLUMNS:
            columns.append(
                {
                    **col,
                    "cards": [c for c in cards if c["column_key"] == col["key"]],
                }
            )
        return {"columns": columns, "cards": cards}

    def add_kanban_card(
        self,
        team_id: str,
        title: str,
        *,
        detail: str = "",
        column_key: str = "backlog",
        priority: str = "med",
        assignee: str = "agent",
    ) -> Dict[str, Any]:
        cid = _id()
        now = _utcnow()
        with self._lock, self._conn() as conn:
            conn.execute(
                "INSERT INTO kanban_cards (id, team_id, title, detail, column_key, priority, assignee, sort_order, created_at, updated_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    cid,
                    team_id,
                    title,
                    detail,
                    column_key,
                    priority,
                    assignee,
                    0,
                    now,
                    now,
                ),
            )
            row = conn.execute(
                "SELECT * FROM kanban_cards WHERE id=?", (cid,)
            ).fetchone()
        self.log_activity(team_id, "kanban_add", title, column_key)
        return dict(row)

    def move_kanban_card(self, card_id: str, column_key: str) -> Dict[str, Any]:
        allowed = {c["key"] for c in self.KANBAN_COLUMNS}
        if column_key not in allowed:
            raise ValueError(f"Invalid column: {column_key}")
        with self._lock, self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM kanban_cards WHERE id=?", (card_id,)
            ).fetchone()
            if not row:
                raise KeyError(card_id)
            conn.execute(
                "UPDATE kanban_cards SET column_key=?, updated_at=? WHERE id=?",
                (column_key, _utcnow(), card_id),
            )
            row = conn.execute(
                "SELECT * FROM kanban_cards WHERE id=?", (card_id,)
            ).fetchone()
        d = dict(row)
        self.log_activity(d["team_id"], "kanban_move", d["title"], column_key)
        return d

    def dashboard(self, slug: str) -> Dict[str, Any]:
        team = self.get_team(slug)
        if not team:
            raise KeyError(slug)
        kpis = self.list_kpis(team["id"])
        kanban = self.list_kanban(team["id"])
        brains = self.list_brains(team["id"])
        skills = self.list_skills(team["id"])
        ideas = [i for i in self.list_ideas(20) if i.get("team_slug") == slug]
        activities = self.list_activities(team["id"])
        flows = self.list_flows(team["id"])
        return {
            "team": team,
            "brains": brains,
            "skills": skills,
            "flows": flows,
            "activities": activities,
            "ideas": ideas,
            "kpis": kpis,
            "kanban": kanban,
            "stats": {
                "brains": len(brains),
                "skills": len(skills),
                "ideas": len(ideas),
                "open_cards": len(
                    [
                        c
                        for c in kanban.get("cards") or []
                        if c.get("column_key") != "done"
                    ]
                ),
                "done_cards": len(
                    [
                        c
                        for c in kanban.get("cards") or []
                        if c.get("column_key") == "done"
                    ]
                ),
                "activities": len(activities),
            },
        }

    def overview(self) -> Dict[str, Any]:
        teams = self.list_teams()
        return {
            "name": "T-ex Agent Workspace",
            "db_path": str(self.path),
            "teams": teams,
            "team_count": len(teams),
            "brain_count": len(self.list_brains()),
            "skill_count": len(self.list_skills()),
            "idea_count": len(self.list_ideas(500)),
            "recent_activity": self.list_activities(limit=15),
        }


_workspace: Optional[WorkspaceDB] = None
_ws_lock = threading.Lock()


def get_workspace() -> WorkspaceDB:
    global _workspace
    with _ws_lock:
        if _workspace is None:
            _workspace = WorkspaceDB()
        return _workspace
