import { NextResponse } from "next/server";

/**
 * Run dispatch proxy — Command Deck ⇄ T-Ex runtime host.
 *
 * The browser never talks to the runtime host directly: this server-side route
 * forwards to it, so the host API key stays in the dashboard's environment
 * (names only in code, values in .env — secrets policy).
 *
 *   TEX_RUNTIME_URL      runtime host base URL (default http://127.0.0.1:3006)
 *   TEX_RUNTIME_API_KEY  host X-API-Key (only needed when the host sets one)
 *
 * POST {team, goal, mode?, workdir?} → host /v1/workspace/teams/{team}/run-async
 * GET  ?id=<jobId>                   → host /v1/jobs/{jobId}
 * GET  ?teams=1                      → host /v1/workspace/teams
 */

const RUNTIME_URL = (process.env.TEX_RUNTIME_URL || "http://127.0.0.1:3006").replace(/\/+$/, "");
const RUNTIME_KEY = process.env.TEX_RUNTIME_API_KEY || "";

const OFFLINE_HINT =
  "Runtime host unreachable. Start it with: cd runtime && source .venv/bin/activate && python -m texllm.cli serve " +
  "(or set TEX_RUNTIME_URL if it runs elsewhere).";

async function hostFetch(path: string, init?: RequestInit, timeoutMs = 8000): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(`${RUNTIME_URL}${path}`, {
      ...init,
      signal: controller.signal,
      cache: "no-store",
      headers: {
        "Content-Type": "application/json",
        ...(RUNTIME_KEY ? { "X-API-Key": RUNTIME_KEY } : {}),
        ...(init?.headers || {}),
      },
    });
  } finally {
    clearTimeout(timer);
  }
}

async function passThrough(res: Response): Promise<NextResponse> {
  const text = await res.text();
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status });
  } catch {
    return NextResponse.json(
      { error: `Runtime host returned non-JSON (${res.status})`, body: text.slice(0, 500) },
      { status: 502 }
    );
  }
}

function offline(): NextResponse {
  return NextResponse.json({ error: "runtime_offline", hint: OFFLINE_HINT }, { status: 502 });
}

export async function GET(request: Request) {
  const url = new URL(request.url);
  const jobId = url.searchParams.get("id");
  const wantTeams = url.searchParams.get("teams");

  try {
    if (jobId) {
      if (!/^[a-zA-Z0-9-]+$/.test(jobId)) {
        return NextResponse.json({ error: "Invalid job id" }, { status: 400 });
      }
      return await passThrough(await hostFetch(`/v1/jobs/${jobId}`));
    }
    if (wantTeams) {
      return await passThrough(await hostFetch(`/v1/workspace/teams`));
    }
    return NextResponse.json({ error: "Pass ?id=<jobId> or ?teams=1" }, { status: 400 });
  } catch {
    return offline();
  }
}

export async function POST(request: Request) {
  let body: { team?: unknown; goal?: unknown; mode?: unknown; workdir?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const team = typeof body.team === "string" ? body.team.trim() : "";
  const goal = typeof body.goal === "string" ? body.goal.trim() : "";
  const mode = body.mode === "code" ? "code" : "chat";
  const workdir = typeof body.workdir === "string" ? body.workdir.trim() : "";

  if (!/^[a-z0-9-]+$/.test(team)) {
    return NextResponse.json({ error: "Invalid team slug" }, { status: 400 });
  }
  if (!goal) {
    return NextResponse.json({ error: "Goal is required" }, { status: 400 });
  }

  try {
    const res = await hostFetch(`/v1/workspace/teams/${team}/run-async`, {
      method: "POST",
      body: JSON.stringify({ goal, mode, ...(workdir ? { workdir } : {}) }),
    });
    return await passThrough(res);
  } catch {
    return offline();
  }
}
