import { FormEvent, useEffect, useState } from "react";

type Consent = {
  id: string; category: "contributor" | "cast" | "production";
  role_label: string; public_name: string; actor_id: string | null; revoked_at: string | null;
};
type Actor = { id: string; display_name: string; status: string };

export default function ProjectCredits({ projectId }: { projectId: string }) {
  const [consents, setConsents] = useState<Consent[]>([]);
  const [actors, setActors] = useState<Actor[]>([]);
  const [category, setCategory] = useState<Consent["category"]>("contributor");
  const [role, setRole] = useState("Story contributor");
  const [name, setName] = useState("");
  const [actorId, setActorId] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const [consentResponse, actorResponse] = await Promise.all([
      fetch(`/api/projects/${projectId}/credit-consents`),
      fetch("/api/actors"),
    ]);
    if (!consentResponse.ok) throw new Error("Could not load credit consents.");
    if (!actorResponse.ok) throw new Error("Could not load your actor profiles.");
    setConsents(await consentResponse.json());
    setActors((await actorResponse.json()).filter((actor: Actor) => actor.status === "active"));
  }
  useEffect(() => { refresh().catch(reason => setError(reason.message)); }, [projectId]);

  async function submit(event: FormEvent) {
    event.preventDefault();
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/projects/${projectId}/credit-consents`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ category, role_label: role, public_name: name, actor_id: category === "cast" ? actorId : null }),
      });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(body?.detail || "Could not save credit consent.");
      setName(""); setActorId("");
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not save credit consent."); }
    finally { setBusy(false); }
  }

  async function revoke(id: string) {
    setBusy(true); setError("");
    try {
      const response = await fetch(`/api/projects/${projectId}/credit-consents/${id}`, { method: "DELETE" });
      const body = await response.json().catch(() => null);
      if (!response.ok) throw new Error(body?.detail || "Could not revoke credit consent.");
      await refresh();
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not revoke credit consent."); }
    finally { setBusy(false); }
  }

  const inputStyle = { width: "100%", boxSizing: "border-box" as const, padding: "10px 12px", borderRadius: 7, border: "1px solid #393941", background: "#17171c", color: "#f4f1eb" };
  return <section style={{ margin: "28px 0", padding: 22, border: "1px solid #34343b", borderRadius: 12, background: "#151519" }}>
    <div className="section-kicker">YOUR PUBLIC CREDIT PREFERENCES</div>
    <h2 style={{ margin: "8px 0" }}>Credits & acknowledgements</h2>
    <p className="muted-note">Only credits you explicitly opt into are included in releases. Revoking consent affects future releases, not releases already published.</p>
    <form onSubmit={submit} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, alignItems: "end", marginTop: 18 }}>
      <label>Credit type<select style={inputStyle} value={category} onChange={event => { const value = event.target.value as Consent["category"]; setCategory(value); setRole(value === "contributor" ? "Story contributor" : value === "cast" ? "Cast" : "Production"); }}><option value="contributor">Contributor</option><option value="cast">Cast / actor</option><option value="production">Production</option></select></label>
      {category === "cast" && <label>Actor profile<select required style={inputStyle} value={actorId} onChange={event => setActorId(event.target.value)}><option value="">Choose your actor</option>{actors.map(actor => <option key={actor.id} value={actor.id}>{actor.display_name}</option>)}</select></label>}
      <label>Role label<input required maxLength={100} style={inputStyle} value={role} onChange={event => setRole(event.target.value)} /></label>
      <label>Public name<input required maxLength={160} style={inputStyle} placeholder="Name to display in credits" value={name} onChange={event => setName(event.target.value)} /></label>
      <button className="primary-button" disabled={busy || !role.trim() || !name.trim() || (category === "cast" && !actorId)} type="submit">{busy ? "Saving…" : "Opt in to this credit"}</button>
    </form>
    {error && <p role="alert" style={{ color: "#e49a8e" }}>{error}</p>}
    <div style={{ marginTop: 20 }}>
      {consents.length === 0 ? <p className="muted-note">You have not opted into any credits for this project.</p> : consents.map(consent => <div key={consent.id} style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 12, padding: "10px 0", borderTop: "1px solid #303037" }}><span><strong>{consent.public_name}</strong> · {consent.role_label} <small style={{ color: "#999" }}>({consent.category}{consent.revoked_at ? " · revoked" : " · active"})</small></span>{!consent.revoked_at && <button className="quiet-button danger-button" disabled={busy} onClick={() => revoke(consent.id)} type="button">Revoke</button>}</div>)}
    </div>
  </section>;
}
