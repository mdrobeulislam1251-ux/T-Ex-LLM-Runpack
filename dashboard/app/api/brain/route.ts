import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";
import { COMPANIES_DIR, BRAINS_WRITABLE, slugify } from "@/lib/data";

/**
 * Smart Brain Generation entry point.
 *
 * The user supplies only what they actually know: the company name and a free-text
 * briefing about structure & vision. This endpoint:
 *   1. creates <TEX_PROJECT_ROOT>/.tex-llm/companies/<slug>/ with a draft profile.json
 *      (env var names pre-derived, values NEVER touched — secrets live in .env only), and
 *   2. writes brain-request.json capturing the briefing verbatim.
 *
 * The T-Ex LLM research team (research-lead, market-analyst, product-strategist) picks up
 * brain-request.json on the next `/onboard <name>` run in Claude Code and generates the
 * full brain — scope, mission, emotion/tone, audience, voice — asking the user only for
 * credentials and brand asset files, which cannot be researched.
 */
export async function POST(request: Request) {
  if (!BRAINS_WRITABLE) {
    return NextResponse.json(
      {
        error:
          "Brains are project-scoped (rule 0): the repo's companies/ holds read-only seeds. " +
          "Set TEX_PROJECT_ROOT to your project folder — the deck then creates the brain in <project>/.tex-llm/companies/.",
      },
      { status: 400 }
    );
  }
  let body: { name?: unknown; briefing?: unknown };
  try {
    body = await request.json();
  } catch {
    return NextResponse.json({ error: "Invalid JSON body" }, { status: 400 });
  }

  const name = typeof body.name === "string" ? body.name.trim() : "";
  const briefing = typeof body.briefing === "string" ? body.briefing.trim() : "";
  if (name.length < 2) {
    return NextResponse.json({ error: "Company name is required" }, { status: 400 });
  }
  if (briefing.length < 20) {
    return NextResponse.json(
      { error: "Tell T-Ex LLM a bit more about the company structure & vision (at least a sentence or two)" },
      { status: 400 }
    );
  }

  const slug = slugify(name);
  if (!slug) {
    return NextResponse.json({ error: "Company name produced an empty slug" }, { status: 400 });
  }

  const companyDir = path.join(COMPANIES_DIR, slug);
  if (fs.existsSync(path.join(companyDir, "profile.json"))) {
    return NextResponse.json({ error: `Company "${slug}" already exists` }, { status: 409 });
  }

  const envPrefix = slug.toUpperCase().replace(/-/g, "_");
  const now = new Date().toISOString();

  const draftProfile = {
    company: { name, slug, app_name: "", description: briefing.split("\n")[0].slice(0, 200), created_at: now },
    brain: {
      scope: { does: "", does_not: "" },
      vision: "",
      mission: "",
      emotion_tone: "",
      target_audience: "",
      voice_examples: [],
      generation: {
        mode: "auto",
        status: "pending-research",
        note: "Run /onboard " + name + " in Claude Code — the research team will generate this brain from brain-request.json.",
      },
    },
    brand: {
      guidelines_file: "brand/brand.md",
      assets_dir: "brand/assets/",
      colors: { primary: "", secondary: "", extra: {} },
      typography: { heading: "", body: "" },
    },
    tech: {
      stack: { frontend: "", backend: "", database: "", mobile: "", cloud: "", decided_by: "" },
      multi_tenant: false,
      compliance_notes: "",
      performance_budgets: { api_p95_ms: 300, lcp_ms: 2500 },
      monthly_cloud_budget_usd: null,
    },
    credentials: {
      _rule: "ENV VAR NAMES ONLY. Raw values live in .env (gitignored). Never store secret values in this file.",
      database: {
        provider: "",
        env: {
          host: `${envPrefix}_DB_HOST`,
          port: `${envPrefix}_DB_PORT`,
          name: `${envPrefix}_DB_NAME`,
          user: `${envPrefix}_DB_USER`,
          password: `${envPrefix}_DB_PASSWORD`,
        },
      },
      n8n: { env: { url: `${envPrefix}_N8N_URL`, api_key: `${envPrefix}_N8N_API_KEY` } },
      other: {},
    },
    logs: { decisions: "decisions.md", incidents: "incidents.md", research_dir: "research/" },
  };

  const brainRequest = {
    requested_at: now,
    source: "tex-dashboard",
    company_name: name,
    user_briefing: briefing,
    instructions:
      "Generate the full company brain from this briefing using the research-strategy skill: " +
      "research-lead frames and sweeps, market-analyst maps the market, product-strategist derives " +
      "scope/vision/mission/differentiation, and content-strategist drafts emotion_tone and voice_examples. " +
      "Fill every empty brain field in profile.json, present the generated brain to the user for a single " +
      "confirm/adjust pass, then ask ONLY for credentials (.env) and brand asset files. Delete this file when done.",
  };

  fs.mkdirSync(path.join(companyDir, "brand", "assets"), { recursive: true });
  fs.mkdirSync(path.join(companyDir, "research"), { recursive: true });
  fs.writeFileSync(path.join(companyDir, "profile.json"), JSON.stringify(draftProfile, null, 2) + "\n");
  fs.writeFileSync(path.join(companyDir, "brain-request.json"), JSON.stringify(brainRequest, null, 2) + "\n");
  for (const log of ["decisions.md", "incidents.md"]) {
    const p = path.join(companyDir, log);
    if (!fs.existsSync(p)) fs.writeFileSync(p, `# ${log.replace(".md", "")} — ${name}\n`);
  }

  const activeFile = path.join(COMPANIES_DIR, "active-company.json");
  fs.writeFileSync(activeFile, JSON.stringify({ active: slug, switched_at: now }, null, 2) + "\n");

  return NextResponse.json({
    ok: true,
    slug,
    next_step: `Brain request created. Run /onboard ${name} in Claude Code — the research team will generate the full brain, then ask only for credentials and brand assets.`,
  });
}
