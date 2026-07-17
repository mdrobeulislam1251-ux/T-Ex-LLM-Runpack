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
                conn.execute(
                    "INSERT OR REPLACE INTO workspace_meta (key, value) VALUES (?,?)",
                    ("name", "T-ex Agent Workspace"),
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

    def dashboard(self, slug: str) -> Dict[str, Any]:
        team = self.get_team(slug)
        if not team:
            raise KeyError(slug)
        return {
            "team": team,
            "brains": self.list_brains(team["id"]),
            "skills": self.list_skills(team["id"]),
            "flows": self.list_flows(team["id"]),
            "activities": self.list_activities(team["id"]),
            "ideas": [i for i in self.list_ideas(20) if i.get("team_slug") == slug],
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
