import { FormEvent, useRef, useState } from "react";
import { FriendlyAgentOnboard } from "../components/FriendlyAgentOnboard";
import { friendlyChat } from "../lib/api";
import { useSettings } from "../state/settings";

type Msg = { role: "user" | "agent"; content: string };

export function ChatPage() {
  const { settings } = useSettings();
  const [messages, setMessages] = useState<Msg[]>([
    {
      role: "agent",
      content:
        "Hi! I'm Tex. Ask about jobs, onboarding, firmware, or how team runners work.",
    },
  ]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  async function onSend(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", content: text }]);
    setBusy(true);
    try {
      const res = await friendlyChat(settings, text);
      setMessages((m) => [...m, res]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div>
      <h1>Friendly chat</h1>
      <p className="lede">
        Warm agent persona over the same host team runners when available.
      </p>
      <FriendlyAgentOnboard
        title="Always kind, always clear"
        message="I avoid jargon when I can and point you to the right console page."
      />
      <div className="card">
        <div className="chat-log" aria-live="polite">
          {messages.map((m, i) => (
            <div key={i} className={"chat-bubble " + m.role}>
              <strong style={{ fontSize: "0.75rem", color: "var(--tex-muted)" }}>
                {m.role === "user" ? "You" : "Tex"}
              </strong>
              <div style={{ whiteSpace: "pre-wrap" }}>{m.content}</div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
        <form onSubmit={onSend} style={{ marginTop: "0.85rem" }}>
          <div className="field">
            <label htmlFor="chat-in">Message</label>
            <textarea
              id="chat-in"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="How do I connect Supabase?"
              rows={3}
            />
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? "Thinking…" : "Send"}
          </button>
        </form>
      </div>
    </div>
  );
}
