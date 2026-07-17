import type { AppSettings } from "../state/settings";

function baseUrl(settings: AppSettings) {
  return (settings.hostUrl || "").replace(/\/$/, "");
}

async function request<T>(
  settings: AppSettings,
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (settings.apiKey) headers.set("X-API-Key", settings.apiKey);
  const res = await fetch(`${baseUrl(settings)}${path}`, { ...init, headers });
  if (!res.ok) throw new Error(`${res.status}: ${await res.text()}`);
  return res.json() as Promise<T>;
}

export type Team = {
  id: string;
  slug: string;
  name: string;
  kind: string;
  description: string;
  color: string;
};

export function workspaceOverview(settings: AppSettings) {
  return request<{
    name: string;
    db_path: string;
    teams: Team[];
    team_count: number;
    brain_count: number;
    skill_count: number;
    idea_count: number;
    recent_activity: { title: string; kind: string; created_at: string }[];
  }>(settings, "/v1/workspace");
}

export function listTeams(settings: AppSettings) {
  return request<{ teams: Team[] }>(settings, "/v1/workspace/teams");
}

export function teamDashboard(settings: AppSettings, slug: string) {
  return request<{
    team: Team;
    brains: { id: string; name: string; role: string; prompt: string }[];
    skills: { id: string; name: string; description: string }[];
    flows: { id: string; name: string; steps: unknown[]; status: string }[];
    activities: { title: string; kind: string; detail: string; created_at: string }[];
    ideas: { title: string; summary: string }[];
  }>(settings, `/v1/workspace/teams/${encodeURIComponent(slug)}`);
}

export function runTeam(settings: AppSettings, slug: string, goal: string) {
  return request<{
    status: string;
    result?: { summary?: string; output?: unknown };
    error?: string;
  }>(settings, `/v1/workspace/teams/${encodeURIComponent(slug)}/run`, {
    method: "POST",
    body: JSON.stringify({ goal }),
  });
}

export function domainReview(
  settings: AppSettings,
  domain: string,
  notes = ""
) {
  return request<{
    domain: string;
    overview: string;
    ideas: unknown[];
    brains: unknown[];
    skills: unknown[];
    fetch_error?: string | null;
  }>(settings, "/v1/workspace/domain-review", {
    method: "POST",
    body: JSON.stringify({ domain, notes }),
  });
}

export function listIdeas(settings: AppSettings) {
  return request<{ ideas: { title: string; team_slug: string; summary: string; domain: string }[] }>(
    settings,
    "/v1/workspace/ideas"
  );
}

export function runPersonalBd(settings: AppSettings, goal: string) {
  return request<{
    status: string;
    result?: { summary?: string; output?: unknown };
    error?: string;
  }>(settings, "/v1/workspace/personal-bd/run", {
    method: "POST",
    body: JSON.stringify({ goal }),
  });
}

export function createTeam(
  settings: AppSettings,
  body: { slug: string; name: string; description?: string; kind?: string }
) {
  return request<Team>(settings, "/v1/workspace/teams", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
