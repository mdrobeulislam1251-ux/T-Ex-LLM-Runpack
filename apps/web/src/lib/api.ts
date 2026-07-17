import type { AppSettings } from "../state/settings";

export type JobStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "cancelled";

export type Handoff = {
  from_role: string;
  to_role?: string | null;
  content: string;
  data?: Record<string, unknown>;
};

export type Job = {
  id: string;
  firmware_id: string;
  firmware_version: string;
  goal: string;
  status: JobStatus;
  error?: string | null;
  result?: {
    summary: string;
    output: Record<string, unknown>;
    review_passed: boolean;
    iterations: number;
    handoffs: Handoff[];
  } | null;
  created_at: string;
  updated_at: string;
};

export type BackendConfigPayload = {
  db: "postgres" | "supabase" | "other" | "none";
  port: string;
  domain: string;
  company: string;
  vision: string;
  theme: string;
  hostUrl?: string;
  apiKey?: string;
};

function baseUrl(settings: AppSettings) {
  return (settings.hostUrl || "").replace(/\/$/, "");
}

async function request<T>(
  settings: AppSettings,
  path: string,
  init: RequestInit = {}
): Promise<T> {
  const url = `${baseUrl(settings)}${path}`;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (settings.apiKey) headers.set("X-API-Key", settings.apiKey);

  const res = await fetch(url, { ...init, headers });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`${res.status}: ${text || res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export function health(settings: AppSettings) {
  return request<{ status: string; version: string }>(settings, "/health");
}

export function createJob(
  settings: AppSettings,
  body: {
    goal: string;
    firmware_id?: string;
    firmware_version?: string;
  }
) {
  return request<Job>(settings, "/v1/jobs", {
    method: "POST",
    body: JSON.stringify({
      firmware_id: body.firmware_id || "sample-assistant",
      firmware_version: body.firmware_version || "0.1.0",
      goal: body.goal,
      input: { goal: body.goal },
    }),
  });
}

export function getJob(settings: AppSettings, id: string) {
  return request<Job>(settings, `/v1/jobs/${id}`);
}

export function listJobs(settings: AppSettings) {
  return request<{ jobs: Job[] }>(settings, "/v1/jobs");
}

export function listFirmware(settings: AppSettings) {
  return request<{ firmware: { id: string; version: string; name: string }[] }>(
    settings,
    "/v1/firmware"
  );
}

/** Persist onboarding config locally; host may add /v1/config later. */
export function saveBackendConfigLocal(config: BackendConfigPayload) {
  localStorage.setItem("texllm.backendConfig.v1", JSON.stringify(config));
  return config;
}

export function loadBackendConfigLocal(): BackendConfigPayload | null {
  try {
    const raw = localStorage.getItem("texllm.backendConfig.v1");
    return raw ? (JSON.parse(raw) as BackendConfigPayload) : null;
  } catch {
    return null;
  }
}

export type AgentAliases = {
  agent_name: string;
  user_name: string;
  agent_aliases: string[];
  user_aliases: string[];
};

export function getAliases(settings: AppSettings) {
  return request<AgentAliases>(settings, "/v1/settings/aliases");
}

export function putAliases(settings: AppSettings, body: AgentAliases) {
  return request<AgentAliases>(settings, "/v1/settings/aliases", {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

/** Friendly chat via team job (or mock offline reply). */
export async function friendlyChat(
  settings: AppSettings,
  message: string,
  aliases?: AgentAliases | null
): Promise<{ role: "agent"; content: string }> {
  const agentName = aliases?.agent_name || "Tex";
  const userName = aliases?.user_name || "Operator";
  try {
    const job = await createJob(settings, {
      goal:
        `You are ${agentName}. Address the user as ${userName}. ` +
        `Friendly support reply (warm, clear, short): ${message}`,
    });
    for (let i = 0; i < 40; i++) {
      await new Promise((r) => setTimeout(r, 200));
      const j = await getJob(settings, job.id);
      if (j.status === "succeeded" && j.result) {
        const answer =
          (j.result.output?.answer as string) ||
          j.result.summary ||
          `I'm here to help, ${userName}.`;
        return { role: "agent", content: answer };
      }
      if (j.status === "failed") break;
    }
  } catch {
    /* fall through */
  }
  return {
    role: "agent",
    content:
      `I'm ${agentName}, your friendly workspace guide. I couldn't reach the host just now — start ` +
      "`python3 -m texllm.cli serve` or check Settings. " +
      `Meanwhile, ${userName}: use Onboarding, Jobs, and Tasks from the sidebar.`,
  };
}
