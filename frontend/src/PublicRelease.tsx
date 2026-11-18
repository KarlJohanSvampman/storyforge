import { useEffect, useState, type CSSProperties, type FormEvent } from "react";

type PublicReleaseData = {
  slug: string; title: string; synopsis: string; visibility: "public" | "unlisted";
  published_at: string; project_title: string; creator_name: string; format: string | null;
  category: string | null; genre: string | null; duration_ms: number | null;
  width: number | null; height: number | null; video_url: string;
  poster_url: string | null; trailer_url: string | null;
  credits: Array<{ category: string; role_label: string; public_name: string; character_name: string | null }>;
};

export default function PublicRelease({ slug }: { slug: string }) {
  const [release, setRelease] = useState<PublicReleaseData | null>(null);
  const [error, setError] = useState("");
  useEffect(() => {
    let active = true;
    fetch(`/api/public/releases/${encodeURIComponent(slug)}`)
      .then(async response => {
        if (!response.ok) throw new Error(response.status === 404 ? "This release is unavailable." : "Could not load this release.");
        return response.json() as Promise<PublicReleaseData>;
      })
      .then(data => { if (active) setRelease(data); })
      .catch(reason => { if (active) setError(reason instanceof Error ? reason.message : "Could not load this release."); });
    return () => { active = false; };
  }, [slug]);

  const shell: CSSProperties = {
    minHeight: "100vh", background: "#101114", color: "#f5f3ef",
    fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif", padding: "clamp(24px, 6vw, 80px)",
    boxSizing: "border-box",
  };
  const content: React.CSSProperties = { maxWidth: 1040, margin: "0 auto" };
  if (error) return <main style={shell}><div style={content}><a href="/" style={{ color: "#c9a77b" }}>← StoryForge</a><h1>Release unavailable</h1><p>{error}</p></div></main>;
  if (!release) return <main style={shell}><div style={content}>Loading release…</div></main>;

  return (
    <main style={shell}>
      <div style={content}>
        <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 20, marginBottom: 56 }}>
          <a href="/" style={{ color: "#e8c99b", textDecoration: "none", letterSpacing: ".16em", fontSize: 13, fontWeight: 700 }}>STORYFORGE</a>
          <a href="/discover" style={{ color: "#a9a6a0", textDecoration: "none", fontSize: 13 }}>Discover works ↗</a>
        </header>
        <div style={{ color: "#c9a77b", fontSize: 12, letterSpacing: ".18em", textTransform: "uppercase" }}>{release.genre || release.category || "A published work"}</div>
        <h1 style={{ fontSize: "clamp(38px, 7vw, 76px)", lineHeight: 1.02, margin: "14px 0 18px", maxWidth: 900 }}>{release.title}</h1>
        <p style={{ color: "#b7b3ad", fontSize: 15, margin: "0 0 8px" }}>
          {release.project_title}{release.format ? ` · ${release.format === "tv_series" ? "TV series" : "Film"}` : ""} · Published {new Date(release.published_at).toLocaleDateString()}
        </p>
        <p style={{ margin: "0 0 28px", color: "#99958e", fontSize: 13 }}>Created by <a href={`/creators/${encodeURIComponent(release.creator_name)}`} style={{ color: "#c9a77b", textDecoration: "none" }}>{release.creator_name}</a></p>
        <video controls playsInline preload="metadata" poster={release.poster_url || undefined} style={{ width: "100%", maxHeight: "70vh", background: "#050505", borderRadius: 8, display: "block" }}>
          <source src={release.video_url} type="video/mp4" />
          Your browser does not support HTML video.
        </video>
        {release.trailer_url && <section style={{ maxWidth: 900, marginTop: 38 }}><h2 style={{ fontSize: 22 }}>Trailer</h2><video controls playsInline preload="metadata" style={{ width: "100%", maxHeight: "55vh", background: "#050505", borderRadius: 8 }}><source src={release.trailer_url} type="video/mp4" /></video></section>}
        {release.credits?.length > 0 && <section style={{ maxWidth: 760, marginTop: 42 }}><h2 style={{ fontSize: 22 }}>Credits</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))", gap: 16 }}>{(["cast", "contributor", "production"] as const).map(category => { const entries = release.credits.filter(credit => credit.category === category); return entries.length ? <div key={category}><h3 style={{ color: "#c9a77b", fontSize: 13, textTransform: "uppercase", letterSpacing: ".12em" }}>{category === "cast" ? "Cast" : category === "contributor" ? "Contributors" : "Production"}</h3>{entries.map((credit, index) => <p key={`${credit.public_name}-${index}`} style={{ margin: "8px 0", color: "#d0cdc7" }}><strong>{credit.public_name}</strong><br /><span style={{ color: "#99958e", fontSize: 13 }}>{credit.role_label}{credit.character_name ? ` · ${credit.character_name}` : ""}</span></p>)}</div> : null; })}</div></section>}
        {release.synopsis && <section style={{ maxWidth: 760, marginTop: 42 }}><h2 style={{ fontSize: 22 }}>Synopsis</h2><p style={{ color: "#d0cdc7", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{release.synopsis}</p></section>}
        <ReleaseFeedback slug={slug} />
        <footer style={{ borderTop: "1px solid #343438", marginTop: 64, paddingTop: 22, color: "#85827d", fontSize: 12 }}>Published with StoryForge · {release.slug}</footer>
      </div>
    </main>
  );
}


type FeedbackReview = {
  id: string; body: string; contains_spoilers: boolean; author_name: string;
  created_at: string; helpful_count: number;
};
type FeedbackData = {
  rating_count: number; average_score: number | null;
  rating_distribution: Record<string, number>; reviews: FeedbackReview[];
};

function ReleaseFeedback({ slug }: { slug: string }) {
  const [feedback, setFeedback] = useState<FeedbackData | null>(null);
  const [score, setScore] = useState("8");
  const [reviewBody, setReviewBody] = useState("");
  const [spoilers, setSpoilers] = useState(false);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState("");

  async function refresh() {
    const response = await fetch(`/api/public/releases/${encodeURIComponent(slug)}/feedback`);
    if (!response.ok) throw new Error("Could not load audience feedback.");
    setFeedback(await response.json());
  }
  useEffect(() => { refresh().catch(error => setNotice(error.message)); }, [slug]);

  async function submitRating(event: FormEvent) {
    event.preventDefault(); setBusy(true); setNotice("");
    try {
      const response = await fetch(`/api/public/releases/${slug}/rating`, {
        method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ score: Number(score) }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(result?.detail || "Could not save rating.");
      await refresh(); setNotice("Your rating has been saved.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not save rating."); }
    finally { setBusy(false); }
  }

  async function submitReview(event: FormEvent) {
    event.preventDefault(); setBusy(true); setNotice("");
    try {
      const response = await fetch(`/api/public/releases/${slug}/review`, {
        method: "PUT", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ body: reviewBody, contains_spoilers: spoilers }),
      });
      const result = await response.json().catch(() => null);
      if (!response.ok) throw new Error(result?.detail || "Could not save review.");
      setReviewBody(""); setSpoilers(false); await refresh(); setNotice("Your review has been saved.");
    } catch (error) { setNotice(error instanceof Error ? error.message : "Could not save review."); }
    finally { setBusy(false); }
  }

  async function helpful(reviewId: string) {
    const response = await fetch(`/api/public/releases/${slug}/reviews/${reviewId}/helpful`, { method: "PUT" });
    const result = await response.json().catch(() => null);
    if (!response.ok) { setNotice(result?.detail || "Could not react to review."); return; }
    await refresh();
  }

  async function report(reviewId: string) {
    const response = await fetch(`/api/public/releases/${slug}/reviews/${reviewId}/reports`, {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ reason: "Inappropriate or abusive content" }),
    });
    const result = await response.json().catch(() => null);
    setNotice(response.ok ? "Thanks. Your report has been recorded." : result?.detail || "Could not report review.");
    await refresh();
  }

  return <section style={{ marginTop: 64, borderTop: "1px solid #343438", paddingTop: 34 }}>
    <div style={{ color: "#c9a77b", fontSize: 12, letterSpacing: ".16em" }}>AUDIENCE</div>
    <h2 style={{ fontSize: 28, margin: "8px 0" }}>Ratings & reviews</h2>
    <div style={{ display: "flex", alignItems: "baseline", gap: 12, marginBottom: 24 }}>
      <strong style={{ fontSize: 34 }}>{feedback?.average_score?.toFixed(1) ?? "—"}</strong>
      <span style={{ color: "#99958e" }}>out of 10 · {feedback?.rating_count ?? 0} ratings</span>
    </div>
    {feedback && <div style={{ maxWidth: 520, display: "grid", gap: 5, marginBottom: 30 }}>{Array.from({ length: 10 }, (_, index) => 10 - index).map(value => <div key={value} style={{ display: "grid", gridTemplateColumns: "22px 1fr 28px", alignItems: "center", gap: 10, fontSize: 12, color: "#a9a6a0" }}><span>{value}</span><div style={{ height: 7, background: "#303037", borderRadius: 8, overflow: "hidden" }}><div style={{ width: `${feedback.rating_count ? feedback.rating_distribution[String(value)] / feedback.rating_count * 100 : 0}%`, height: "100%", background: "#c9a77b" }} /></div><span>{feedback.rating_distribution[String(value)]}</span></div>)}</div>}
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))", gap: 18, maxWidth: 850 }}>
      <form onSubmit={submitRating} style={{ background: "#17171c", padding: 18, borderRadius: 9, display: "grid", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Rate this release</h3>
        <label>Your score<select value={score} onChange={event => setScore(event.target.value)}>{Array.from({ length: 10 }, (_, index) => index + 1).map(value => <option key={value} value={value}>{value} / 10</option>)}</select></label>
        <button disabled={busy} type="submit">Save rating</button>
      </form>
      <form onSubmit={submitReview} style={{ background: "#17171c", padding: 18, borderRadius: 9, display: "grid", gap: 12 }}>
        <h3 style={{ margin: 0 }}>Write or update your review</h3>
        <textarea rows={5} maxLength={10000} required value={reviewBody} onChange={event => setReviewBody(event.target.value)} placeholder="What did you think?" />
        <label style={{ display: "flex", gap: 8, alignItems: "center" }}><input type="checkbox" checked={spoilers} onChange={event => setSpoilers(event.target.checked)} /> Contains spoilers</label>
        <button disabled={busy || !reviewBody.trim()} type="submit">Save review</button>
      </form>
    </div>
    {notice && <p role="status" style={{ color: "#c9a77b" }}>{notice}</p>}
    <div style={{ maxWidth: 850, display: "grid", gap: 12, marginTop: 26 }}>
      {feedback?.reviews.map(review => <article key={review.id} style={{ border: "1px solid #343438", borderRadius: 9, padding: 18 }}>
        <div style={{ display: "flex", justifyContent: "space-between", gap: 12, color: "#99958e", fontSize: 12 }}><strong>{review.author_name}</strong><span>{new Date(review.created_at).toLocaleDateString()}</span></div>
        {review.contains_spoilers ? <details style={{ marginTop: 12 }}><summary style={{ cursor: "pointer", color: "#c9a77b" }}>Spoiler review — reveal</summary><p style={{ lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{review.body}</p></details> : <p style={{ lineHeight: 1.7, whiteSpace: "pre-wrap" }}>{review.body}</p>}
        <div style={{ display: "flex", gap: 12, fontSize: 12 }}><button type="button" onClick={() => helpful(review.id)}>Helpful · {review.helpful_count}</button><button type="button" onClick={() => report(review.id)}>Report</button></div>
      </article>)}
      {feedback && feedback.reviews.length === 0 && <p style={{ color: "#99958e" }}>No reviews yet. Be the first to share your thoughts.</p>}
    </div>
  </section>;
}
