import { FormEvent, useState } from "react";
import { Link } from "react-router-dom";
import { domainReview } from "../lib/workspace";
import { useSettings } from "../state/settings";

export function DomainReviewPage() {
  const { settings } = useSettings();
  const [domain, setDomain] = useState("");
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const [out, setOut] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    setOut(null);
    try {
      const r = await domainReview(settings, domain.trim(), notes.trim());
      setOut(JSON.stringify(r, null, 2));
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <p>
        <Link to="/workspace">← Workspace</Link>
      </p>
      <h1>Domain / website review</h1>
      <p className="lede">
        Analyze a site or domain, generate product ideas, and auto-create{" "}
        <strong>brains</strong> and <strong>skills</strong> for team agents —
        stored in the shared workspace DB.
      </p>

      <form className="card" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="dom">Domain or URL</label>
          <input
            id="dom"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            placeholder="example.com"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="notes">Notes</label>
          <textarea
            id="notes"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="B2B SaaS, focus on sales + fulfillment"
          />
        </div>
        <button className="btn btn-primary" type="submit" disabled={busy}>
          {busy ? "Reviewing (uses Claude if connected)…" : "Generate ideas & brains"}
        </button>
      </form>

      {error && (
        <div className="status-banner error" style={{ marginTop: "1rem" }}>
          {error}
        </div>
      )}
      {out && (
        <pre className="card mono" style={{ marginTop: "1rem", whiteSpace: "pre-wrap" }}>
          {out}
        </pre>
      )}

      <p className="empty-hint">
        CLI: <span className="mono">tex review example.com --notes "…"</span>
      </p>
    </div>
  );
}
