#!/usr/bin/env node
/**
 * hooks/chat-capture.mjs — T-Ex LLM realtime chat-brain (Stop hook).
 * On every completed turn, extract that turn from the transcript, redact secrets, and
 * append it to a durable log: always local JSONL (.claude/chat-log.jsonl), and best-effort
 * to a DB table when CHATBRAIN_DB_URL + CHATBRAIN_DB_KEY (or SUPABASE_URL/NEXT_PUBLIC_SUPABASE_URL
 * + SUPABASE_SERVICE_ROLE_KEY) are set. Never throws, always exits 0.
 * Modes: (default) read Stop payload on stdin | --dry-run print only | --transcript <path>
 */
import { readFileSync, writeFileSync, appendFileSync, existsSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";
import { execSync } from "node:child_process";

const LOG = ".claude/chat-log.jsonl";
const CURSOR = ".claude/chat-log.cursor";
const CHAT_MAX = 1000;
const DRY = process.argv.includes("--dry-run");

const e = (() => { const o = {}; try { readFileSync(".env.local", "utf8").split(/\r?\n/).forEach((l) => { const m = l.match(/^([A-Z_]+)=(.*)$/); if (m) o[m[1]] = m[2]; }); } catch {} return { ...o, ...process.env }; })();
const DB_URL = e.CHATBRAIN_DB_URL || e.SUPABASE_URL || e.NEXT_PUBLIC_SUPABASE_URL || "";
const DB_KEY = e.CHATBRAIN_DB_KEY || e.SUPABASE_SERVICE_ROLE_KEY || "";
const DB_SCHEMA = e.CHATBRAIN_DB_SCHEMA || e.NEXT_PUBLIC_SUPABASE_SCHEMA || "";
const TABLE = e.CHATBRAIN_TABLE || "arion_chatlog";

const SECRET_RE = [/sk_live_[0-9A-Za-z]+/g, /sk_(?:live|test)_[0-9A-Za-z]+/g, /rk_(?:live|test)_[0-9A-Za-z]+/g, /whsec_[0-9A-Za-z]+/g, /sb_(?:secret|publishable)_[0-9A-Za-z_-]+/g, /eyJ[0-9A-Za-z_-]{20,}\.[0-9A-Za-z_.-]+/g, /gh[pousr]_[0-9A-Za-z]{20,}/g, /AKIA[0-9A-Z]{16}/g];
const redact = (s) => { let o = String(s ?? ""); for (const re of SECRET_RE) o = o.replace(re, (m) => { const c = m.indexOf("_", 3); return (c > 0 ? m.slice(0, c + 1) : m.slice(0, 4)) + "***"; }); return o; };
const branch = (() => { try { return execSync("git rev-parse --abbrev-ref HEAD", { stdio: ["ignore", "pipe", "ignore"] }).toString().trim(); } catch { return null; } })();
const clip = (s, n) => { const t = String(s ?? "").replace(/\[[0-9;]*m/g, "").replace(/\s+/g, " ").trim(); return t.length > n ? t.slice(0, n - 1) + "…" : t; };
const isMachineChatter = (t) => /<command-(name|message|args)>|<local-command-(stdout|caveat)>|<user-prompt-submit-hook>|<task-notification|<task-id|<system-reminder>/.test(t);
const textOf = (msg) => { const c = msg?.content; if (typeof c === "string") return c; if (!Array.isArray(c)) return ""; return c.filter((b) => b && b.type === "text" && typeof b.text === "string").map((b) => b.text).join(" "); };
const HARNESSES = [["typecheck", /tsc\s+--noEmit/], ["browser-drive", /scripts\/drive\.mjs/], ["screenshots", /scripts\/shots\.mjs/], ["tenant-isolation", /scripts\/isolation\.mjs/], ["live-state", /scripts\/livestate\.mjs/], ["http-probe", /\bcurl\s+-s?[A-Za-z]*\s+http/], ["tests", /\b(vitest|jest|playwright test|npm test)\b/]];
const BLOCK_PATTERNS = [["scope-block", /BLOCKED by gate/], ["design-gate", /DESIGN GATE —/]];

const readStdin = () => new Promise((resolve) => { let s = ""; process.stdin.setEncoding("utf8"); process.stdin.on("data", (d) => (s += d)); process.stdin.on("end", () => resolve(s)); setTimeout(() => resolve(s), 3000).unref?.(); });

function newestTranscript() {
  const root = join(process.env.HOME || "", ".claude", "projects");
  let best = null;
  try { for (const dir of readdirSync(root)) { const d = join(root, dir); for (const f of readdirSync(d)) { if (!f.endsWith(".jsonl")) continue; const p = join(d, f); const m = statSync(p).mtimeMs; if (!best || m > best.m) best = { p, m }; } } } catch {}
  return best?.p ?? null;
}

function parseLastTurn(path) {
  let raw; try { raw = readFileSync(path, "utf8"); } catch { return null; }
  const msgs = [];
  for (const line of raw.split("\n")) { if (!line.trim()) continue; let d; try { d = JSON.parse(line); } catch { continue; } if (d.isSidechain) continue; msgs.push(d); }
  let uIdx = -1, userText = "", userTs = null;
  for (let i = msgs.length - 1; i >= 0; i--) { const d = msgs[i]; if (d.type !== "user" || d.isMeta) continue; const t = textOf(d.message); if (!t.trim() || isMachineChatter(t)) continue; uIdx = i; userText = t; userTs = d.timestamp || null; break; }
  if (uIdx === -1) return null;
  const asst = [], tools = {}, files = new Set(), harnesses = {}, blocks = {};
  for (let i = uIdx + 1; i < msgs.length; i++) {
    const d = msgs[i];
    if (d.type === "user" && !d.isMeta) { const t = textOf(d.message); if (t.trim() && !isMachineChatter(t)) break; }
    if (d.type === "assistant" && Array.isArray(d.message?.content)) {
      for (const b of d.message.content) {
        if (!b) continue;
        if (b.type === "text" && typeof b.text === "string") asst.push(b.text);
        if (b.type !== "tool_use") continue;
        tools[b.name] = (tools[b.name] || 0) + 1;
        const input = b.input || {};
        if (b.name === "Bash" && typeof input.command === "string") for (const [n, re] of HARNESSES) if (re.test(input.command)) harnesses[n] = (harnesses[n] || 0) + 1;
        if ((b.name === "Edit" || b.name === "Write" || b.name === "NotebookEdit") && input.file_path) files.add(String(input.file_path).replace(/^.*\/workspace\//, ""));
      }
    }
    if (d.type === "system" && typeof d.content === "string") for (const [k, re] of BLOCK_PATTERNS) if (re.test(d.content)) blocks[k] = (blocks[k] || 0) + 1;
  }
  return { ts: userTs, user: clip(redact(userText), 4000), assistant: clip(redact(asst.join(" ")), 8000), tools, files: [...files].slice(0, 40), harnesses, blocks };
}

async function postTurn(row) {
  if (!DB_URL || !DB_KEY) return { ok: false, status: 0 };
  try {
    const headers = { apikey: DB_KEY, Authorization: "Bearer " + DB_KEY, "Content-Type": "application/json", Prefer: "return=minimal" };
    if (DB_SCHEMA) headers["Content-Profile"] = DB_SCHEMA;
    const r = await fetch(`${DB_URL}/rest/v1/${TABLE}`, { method: "POST", headers, body: redact(JSON.stringify([row])), signal: AbortSignal.timeout(3000) });
    return { ok: r.ok, status: r.status };
  } catch { return { ok: false, status: 0 }; }
}

function appendBounded(line) { try { appendFileSync(LOG, line + "\n"); const lines = readFileSync(LOG, "utf8").split(/\r?\n/).filter(Boolean); if (lines.length > CHAT_MAX) writeFileSync(LOG, lines.slice(lines.length - CHAT_MAX).join("\n") + "\n"); } catch {} }

async function main() {
  let payload = {}; try { payload = JSON.parse((await readStdin()) || "{}"); } catch {}
  const tFlag = process.argv.indexOf("--transcript");
  const tPath = tFlag !== -1 ? process.argv[tFlag + 1] : (payload.transcript_path || "").replace(/\\\\/g, "/") || newestTranscript();
  if (!tPath || !existsSync(tPath)) return;
  const turn = parseLastTurn(tPath);
  if (!turn || (!turn.user && !turn.assistant)) return;
  let last = null; try { last = readFileSync(CURSOR, "utf8").trim(); } catch {}
  if (turn.ts && last === turn.ts && !DRY) return;
  const row = { branch, session_id: payload.session_id ?? null, ts: turn.ts, user_text: turn.user, assistant_text: turn.assistant, tools: turn.tools, files: turn.files, harnesses: turn.harnesses, blocks: turn.blocks };
  if (DRY) { console.log(redact(JSON.stringify(row, null, 2))); return; }
  appendBounded(JSON.stringify(row));
  await postTurn(row);
  try { if (turn.ts) writeFileSync(CURSOR, turn.ts); } catch {}
}

try { await main(); } catch {} finally { process.exit(0); }
