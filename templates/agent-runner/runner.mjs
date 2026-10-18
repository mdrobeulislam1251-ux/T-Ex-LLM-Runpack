// tex-agent-runner — event-driven Claude fixer.
// Triggered ONCE per Linear issue (by n8n, token-gated). No polling.
// Runs headless Claude as the unprivileged `texagent` user, on a branch only,
// and reports back to Linear THROUGH the n8n gateway (never holds the Linear key).
// Node 20+ (uses global fetch). Zero npm dependencies — built-ins only.
import http from 'node:http';
import { spawn } from 'node:child_process';
import fs from 'node:fs';
import path from 'node:path';

const ENV = process.env;
const PORT = parseInt(ENV.RUNNER_PORT || '8787', 10);
const BIND = ENV.RUNNER_BIND || '0.0.0.0';
const TOKEN = ENV.RUNNER_TOKEN || '';
const N8N_BASE = ENV.N8N_BASE || 'http://127.0.0.1:5678';
const GATEWAY_TOKEN = ENV.TEX_GATEWAY_TOKEN || '';
const REPO_URL = ENV.REPO_URL || '';
const GH_TOKEN = ENV.GH_TOKEN || '';
const BASE_BRANCH = ENV.DEFAULT_BASE_BRANCH || 'main';
const OAUTH = ENV.CLAUDE_CODE_OAUTH_TOKEN || '';
const WORK = path.join(ENV.HOME || '/home/texagent', 'work');

fs.mkdirSync(WORK, { recursive: true });
let busy = false;
const log = (...a) => console.log(new Date().toISOString(), ...a);

function sh(cmd, args, opts = {}) {
  return new Promise((resolve) => {
    const p = spawn(cmd, args, { ...opts, env: { ...ENV, ...(opts.env || {}) } });
    let out = '', err = '';
    p.stdout.on('data', d => (out += d));
    p.stderr.on('data', d => (err += d));
    p.on('close', code => resolve({ code, out, err }));
    p.on('error', e => resolve({ code: 1, out, err: String(e) }));
  });
}

async function gateway(query, variables) {
  const res = await fetch(`${N8N_BASE}/webhook/tex-claude-gateway`, {
    method: 'POST',
    headers: { 'content-type': 'application/json', 'x-tex-token': GATEWAY_TOKEN },
    body: JSON.stringify({ query, variables }),
  });
  return res.json().catch(() => ({}));
}

async function comment(issueId, body) {
  if (!issueId) return;
  await gateway(
    'mutation($id:String!,$body:String!){commentCreate(input:{issueId:$id,body:$body}){success}}',
    { id: issueId, body: body.slice(0, 4000) }
  ).catch(e => log('comment failed', e));
}

function authedRepo(url) {
  if (GH_TOKEN && url.startsWith('https://github.com/'))
    return url.replace('https://github.com/', `https://x-access-token:${GH_TOKEN}@github.com/`);
  return url;
}

async function runJob(job) {
  const { identifier = 'issue', title = '', description = '', issueId, repo } = job;
  const repoUrl = repo || REPO_URL;
  const name = (repoUrl.split('/').pop() || 'repo').replace(/\.git$/, '');
  const dir = path.join(WORK, name);
  const branch = `claude/${identifier.toLowerCase()}`;
  log('job start', identifier);
  try {
    if (!fs.existsSync(path.join(dir, '.git'))) {
      const c = await sh('git', ['clone', authedRepo(repoUrl), dir]);
      if (c.code) throw new Error('clone failed: ' + c.err.slice(0, 300));
    }
    await sh('git', ['-C', dir, 'remote', 'set-url', 'origin', authedRepo(repoUrl)]);
    await sh('git', ['-C', dir, 'fetch', 'origin', BASE_BRANCH]);
    await sh('git', ['-C', dir, 'checkout', '-B', branch, `origin/${BASE_BRANCH}`]);
    await sh('git', ['-C', dir, 'config', 'user.email', 'texagent@datryxen']);
    await sh('git', ['-C', dir, 'config', 'user.name', 'TEX Agent']);

    const prompt = [
      `You are fixing Linear issue ${identifier}: ${title}`, '',
      description, '',
      'Rules: work ONLY inside this repository. Make the change, then run any acceptance',
      'checks named in the issue. Keep the diff minimal and focused. When done, stop.',
    ].join('\n');

    const r = await sh('claude', [
      '-p', prompt,
      '--output-format', 'json',
      '--permission-mode', 'acceptEdits',
      '--allowedTools', 'Read,Edit,Write,Grep,Glob,Bash',
    ], { cwd: dir, env: OAUTH ? { CLAUDE_CODE_OAUTH_TOKEN: OAUTH } : {} });

    let summary = '';
    try { summary = JSON.parse(r.out).result || ''; } catch { summary = (r.out || r.err).slice(-1500); }

    const st = await sh('git', ['-C', dir, 'status', '--porcelain']);
    if (!st.out.trim()) {
      await comment(issueId, `🤖 Claude ran on **${identifier}** but made no changes.\n\n${summary}`);
      log('job done (no changes)', identifier); return;
    }
    await sh('git', ['-C', dir, 'add', '-A']);
    await sh('git', ['-C', dir, 'commit', '-m', `${identifier}: ${title}\n\nAutomated fix by TEX agent-runner.`]);

    let pushed = false;
    if (GH_TOKEN) {
      const pu = await sh('git', ['-C', dir, 'push', '-u', 'origin', branch, '--force-with-lease']);
      pushed = pu.code === 0;
      if (!pushed) log('push failed', pu.err.slice(0, 300));
    }
    await comment(issueId, pushed
      ? `🤖 Claude fixed **${identifier}** on branch \`${branch}\` (pushed). Open a PR to review — nothing auto-merges.\n\n${summary}`
      : `🤖 Claude changed files for **${identifier}** on local branch \`${branch}\` (not pushed — set GH_TOKEN to enable push).\n\n${summary}`);
    log('job done', identifier, 'pushed=' + pushed);
  } catch (e) {
    log('job error', identifier, e);
    await comment(issueId, `🤖 agent-runner error on **${identifier}**: ${String(e).slice(0, 500)}`);
  }
}

const server = http.createServer((req, res) => {
  if (req.method === 'GET' && req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    return res.end(JSON.stringify({ ok: true, authed: !!OAUTH, busy }));
  }
  if (req.method === 'POST' && req.url === '/run') {
    if (!TOKEN || (req.headers['x-tex-runner-token'] || '') !== TOKEN) {
      res.writeHead(401); return res.end('unauthorized');
    }
    let body = '';
    req.on('data', d => (body += d));
    req.on('end', () => {
      let job;
      try { job = JSON.parse(body); } catch { res.writeHead(400); return res.end('bad json'); }
      if (busy) { res.writeHead(409); return res.end(JSON.stringify({ accepted: false, reason: 'busy' })); }
      busy = true;
      res.writeHead(202, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ accepted: true, identifier: job.identifier }));
      runJob(job).finally(() => { busy = false; });
    });
    return;
  }
  res.writeHead(404); res.end('not found');
});
server.listen(PORT, BIND, () => log(`tex-agent-runner on ${BIND}:${PORT} authed=${!!OAUTH}`));
