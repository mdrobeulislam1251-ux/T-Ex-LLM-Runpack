# Messaging Channels — drive T-Ex from chat

Dispatch and manage team runs from **Telegram, WhatsApp, Google Chat, iMessage
(via BlueBubbles), or any custom tool**: text `run dev --code fix the parser`
from your phone, the team runs on the host, and the result (summary + files
changed) lands back in the same chat.

> Naming note: these are *messaging* channels for run dispatch — unrelated to
> the outbound engine's List/Mailbox/Track slots in the plugin doctrine.

## Command grammar

| Message | Effect |
|---|---|
| `run <team> <goal…>` | Dispatch a draft (chat-mode) run |
| `run <team> --code <goal…>` | Dispatch a **code** run — real file edits + diff artifacts |
| `status <job-id-prefix>` | One job's state (+ files changed for code runs) |
| `teams` | List workspace teams |
| `jobs` | Last 5 jobs on this host |
| `help` | Grammar reminder |
| anything else | Draft run on `CHANNELS_DEFAULT_TEAM` (unset → help reply) |

Leading `/` and `@BotName` mentions are stripped, so `/run dev x` and
`@TexBot run dev x` both work. Every dispatch is acknowledged with a short job
id; the completion is pushed back to the same chat when the run finishes.

`--workdir` is **deliberately not accepted from chat**: a remote sender must
never point code-mode at an arbitrary host path. Chat code runs always use the
isolated `.texllm/runs/<job-id>/` scratch dir; in-place work stays on the CLI.

## Security model (read before enabling anything)

- **Default-deny allowlists.** Each channel has a `*_ALLOWED_SENDERS` env var
  (comma-separated platform ids). Empty = every message is dropped silently.
  Unallowlisted senders get **no reply at all** — no probing oracle.
- **Platform-native verification.** Webhook routes live OUTSIDE the host
  `X-API-Key` gate on purpose (platforms can't send custom headers); instead
  each adapter verifies its platform's own mechanism over the raw bytes:
  Telegram secret-token header, WhatsApp HMAC signature, Google Chat JWT,
  BlueBubbles shared password, custom HMAC. All comparisons use
  `hmac.compare_digest`.
- **Code mode from chat** is gated by the same allowlist (there is no second
  tier: if you allowlist a sender, they can run `--code`). Keep allowlists to
  yourself and your operators.
- **Secrets policy** (repo rule): env var *names* in code and docs, values
  only in `.env`. The `GET /v1/channels` status endpoint reports counts and
  flags, never values.
- `status`/`jobs` show all jobs on the host, not per-sender — this is a
  single-operator surface.
- In group chats, the allowlist applies to the *sender*, but replies go to the
  group thread (visible to all members).

## Host API

| Method | Path | Auth |
|---|---|---|
| GET | `/v1/channels` | X-API-Key — adapter status (counts/flags only) |
| GET | `/v1/channels/{channel}/webhook` | platform (WhatsApp handshake) |
| POST | `/v1/channels/{channel}/webhook` | platform (signature/secret/JWT) |

Channels: `telegram`, `whatsapp`, `google_chat`, `bluebubbles`, `custom`, plus
anything registered via `CHANNEL_PLUGINS`.

## Telegram — the no-public-URL quickstart

1. Create a bot with @BotFather → copy the token.
2. Get your numeric user id (message @userinfobot).
3. In `runtime/.env`: `TELEGRAM_BOT_TOKEN=…`, `TELEGRAM_ALLOWED_SENDERS=<your id>`.
4. `tex channels poll telegram` — long-poll worker, **no public URL, no
   webhook secret needed**. Text the bot: `teams`, then `run dev Draft a
   release checklist`, then `status <id8>`.

Webhook alternative (needs public HTTPS): set `TELEGRAM_WEBHOOK_SECRET`, then
call Telegram's `setWebhook` with `url=https://<host>/v1/channels/telegram/webhook`
and `secret_token=<the same secret>`. Webhook and getUpdates are mutually
exclusive — the poller raises an actionable 409 error if a webhook is set.

Convenience: `TELEGRAM_POLL_ON_SERVE=true` runs the poller inside
`texllm serve` (only when no webhook secret is configured).

**Caveat:** a standalone poller process and a `serve` process each own an
independent in-memory job store — chat `status`/`jobs` only see jobs
dispatched through the same process. Run one or the other.

## WhatsApp (Meta Cloud API)

1. Meta developer app → WhatsApp product → copy the **access token**,
   **phone number id**, and **app secret**; invent a **verify token**.
2. `.env`: `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_APP_SECRET`,
   `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN`,
   `WHATSAPP_ALLOWED_SENDERS=15551234567` (wa_id digits).
3. In Meta's webhook config point to
   `https://<host>/v1/channels/whatsapp/webhook` — the GET handshake echoes
   `hub.challenge` when your verify token matches; POSTs are verified via
   `X-Hub-Signature-256` (HMAC-SHA256 of the raw body with the app secret).

## Google Chat

1. Google Cloud project → enable the Chat API → configure a Chat app with an
   HTTP endpoint: `https://<host>/v1/channels/google_chat/webhook`.
2. `.env`: `GOOGLE_CHAT_PROJECT_NUMBER=<project number>` (the JWT audience),
   `GOOGLE_CHAT_ALLOWED_SENDERS=users/<id>,you@company.com` (ids and/or emails).
3. Replies to commands ride back **synchronously** in the HTTP response — no
   outbound Google dependency. For run-completion pushes, create a space
   **incoming webhook** and set `GOOGLE_CHAT_SPACE_WEBHOOK_URL`; without it,
   completions are skipped and you poll with `status <id8>`.

v1 verifies the bearer JWT via Google's tokeninfo endpoint (one HTTPS round
trip per event; needs egress). Offline verification via `google-auth` is a
planned optional extra.

## iMessage via BlueBubbles (the honest story)

Apple ships **no public iMessage API**. The supported path is
[BlueBubbles](https://bluebubbles.app): a community server that runs **on a
Mac you own** and relays iMessage. Unofficial — macOS updates can break it.

1. Install BlueBubbles server on the Mac, set its password, enable webhooks →
   point them at `http(s)://<host>/v1/channels/bluebubbles/webhook?password=<pw>`.
2. `.env`: `BLUEBUBBLES_URL=http://<mac>:1234`, `BLUEBUBBLES_PASSWORD=<pw>`,
   `BLUEBUBBLES_ALLOWED_SENDERS=+15551234567`.
3. Keep the link private (HTTPS or a tailnet) — BlueBubbles webhooks are
   password-authenticated, not signed. Sends use the `private-api` method
   (enable the BlueBubbles helper; fallback: `apple-script`).

The adapter skips `isFromMe` events — mandatory, otherwise the bot's own
replies loop back as commands.

## Custom channel — make anything a channel

Generic HMAC webhook, and the reference for writing real adapters:

```bash
BODY='{"sender":"ops-bot","text":"run dev fix the flaky test","reply_url":"https://your-tool/hook"}'
SIG=$(printf '%s' "$BODY" | openssl dgst -sha256 -hmac "$CUSTOM_CHANNEL_SECRET" | awk '{print $2}')
curl -s -X POST "http://127.0.0.1:3006/v1/channels/custom/webhook" \
  -H "Content-Type: application/json" -H "X-Tex-Channel-Signature: $SIG" -d "$BODY"
# → {"text": "Queued chat run on dev — job 1a2b3c4d\ncheck: status 1a2b3c4d"}
```

The ack returns synchronously; the completion is POSTed to `reply_url` as
`{"text": …}` signed with the same header, so your tool can verify T-Ex back.

### Writing a full adapter (third-party plugin)

```python
# yourpkg/tex_channel.py
from texllm.channels.base import ChannelAdapter, InboundMessage, WebhookRequest
from texllm.channels.registry import register_adapter

class SignalAdapter(ChannelAdapter):
    name = "signal"
    @classmethod
    def from_settings(cls, settings):  # None = not configured on this host
        ...
    def verify_and_parse(self, req: WebhookRequest):  # raise ChannelVerifyError on bad auth
        ...
    def send(self, chat_ref: str, text: str):  # completion pushes
        ...

register_adapter(SignalAdapter)
```

Set `CHANNEL_PLUGINS=yourpkg.tex_channel` — the module is imported (and the
adapter registered) when the host builds its channel table. No core edits.

## Completion push semantics & v1 limits

- The ack always includes `status <id8>` — that's the manual fallback whenever
  a push can't happen (adapter can't push, transport down, host restarted).
- Jobs live in the in-memory store: a host restart loses history and any
  not-yet-fired pushes. A push is a single attempt; failures are logged, never
  retried, and never affect the stored job result.
- No message-id dedup yet: if a platform redelivers a webhook, a `run` command
  can double-dispatch (platforms retry on non-2xx; we always answer 200 after
  verification, so this is rare).

## Follow-ups (not in v1)

Media/attachments · per-sender rate limits · message-id dedup LRU · push
retries / persistent job store · thread-aware replies · Slack/Discord/Signal
adapters · Google Chat offline JWT verify (`google-auth` extra) · n8n-fronted
channel templates · dashboard Channels status card.
