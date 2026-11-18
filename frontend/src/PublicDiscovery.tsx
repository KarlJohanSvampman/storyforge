import { FormEvent, useEffect, useState } from "react";

type DiscoveryRelease = {
  slug: string; title: string; synopsis: string; project_title: string;
  creator_name: string; genre: string; category: string; format: string;
  published_at: string; poster_url: string | null; average_score: number | null;
  rating_count: number;
};

export default function PublicDiscovery() {
  const [releases, setReleases] = useState<DiscoveryRelease[]>([]);
  const [genre, setGenre] = useState("");
  const [creator, setCreator] = useState("");
  const [category, setCategory] = useState("");
  const [sort, setSort] = useState("recent");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function search(event?: FormEvent) {
    event?.preventDefault();
    setLoading(true); setError("");
    const params = new URLSearchParams();
    if (genre.trim()) params.set("genre", genre.trim());
    if (creator.trim()) params.set("creator", creator.trim());
    if (category) params.set("category", category);
    params.set("sort", sort);
    try {
      const response = await fetch(`/api/public/releases?${params.toString()}`);
      if (!response.ok) throw new Error("Could not load public releases.");
      setReleases(await response.json());
    } catch (reason) { setError(reason instanceof Error ? reason.message : "Could not load public releases."); }
    finally { setLoading(false); }
  }
  useEffect(() => { search(); }, []);

  return <main style={{ minHeight: "100vh", background: "#101114", color: "#f5f3ef", padding: "clamp(24px, 6vw, 80px)", boxSizing: "border-box", fontFamily: "Inter, ui-sans-serif, system-ui, sans-serif" }}>
    <div style={{ maxWidth: 1160, margin: "0 auto" }}>
      <header style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 56 }}>
        <a href="/" style={{ color: "#e8c99b", textDecoration: "none", letterSpacing: ".16em", fontSize: 13, fontWeight: 700 }}>STORYFORGE</a>
        <a href="/" style={{ color: "#a9a6a0", textDecoration: "none" }}>Back to workspace</a>
      </header>
      <div style={{ color: "#c9a77b", fontSize: 12, letterSpacing: ".18em" }}>THE COLLECTIVE'S PUBLIC WORKS</div>
      <h1 style={{ fontSize: "clamp(38px, 7vw, 72px)", margin: "12px 0" }}>Discover stories.</h1>
      <p style={{ color: "#aaa69f", maxWidth: 650, lineHeight: 1.7 }}>Explore films, series and documentaries published by the StoryForge community.</p>
      <form onSubmit={search} style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 12, padding: 18, background: "#17171c", borderRadius: 10, margin: "30px 0 38px" }}>
        <label>Genre<input value={genre} onChange={event => setGenre(event.target.value)} placeholder="e.g. Science fiction" /></label>
        <label>Creator<input value={creator} onChange={event => setCreator(event.target.value)} placeholder="Creator name" /></label>
        <label>Category<select value={category} onChange={event => setCategory(event.target.value)}><option value="">All categories</option><option value="fiction">Fiction</option><option value="documentary">Documentary</option></select></label>
        <label>Sort by<select value={sort} onChange={event => setSort(event.target.value)}><option value="recent">Recently published</option><option value="popular">Most popular</option><option value="top_rated">Top rated</option></select></label>
        <button type="submit" disabled={loading}>{loading ? "Searching…" : "Find releases"}</button>
      </form>
      {error && <p role="alert" style={{ color: "#e49a8e" }}>{error}</p>}
      <div style={{ display: "flex", justifyContent: "space-between", color: "#99958e", fontSize: 13, marginBottom: 16 }}><span>{releases.length} releases</span><span>Public releases only</span></div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))", gap: 22 }}>
        {releases.map(release => <a key={release.slug} href={`/releases/${release.slug}`} style={{ color: "inherit", textDecoration: "none", background: "#17171c", borderRadius: 10, overflow: "hidden", border: "1px solid #303037" }}>
          {release.poster_url ? <img src={release.poster_url} alt="" style={{ width: "100%", aspectRatio: "16 / 9", objectFit: "cover", display: "block" }} /> : <div style={{ aspectRatio: "16 / 9", display: "grid", placeItems: "center", background: "#24242b", color: "#c9a77b" }}>STORYFORGE</div>}
          <div style={{ padding: 17 }}>
            <div style={{ color: "#c9a77b", fontSize: 11, textTransform: "uppercase", letterSpacing: ".12em" }}>{release.genre || release.category} · {release.format === "tv_series" ? "Series" : "Film"}</div>
            <h2 style={{ fontSize: 21, margin: "9px 0" }}>{release.title}</h2>
            <p style={{ color: "#aaa69f", fontSize: 13, lineHeight: 1.55, minHeight: 40 }}>{release.synopsis.slice(0, 120)}{release.synopsis.length > 120 ? "…" : ""}</p>
            <div style={{ color: "#99958e", fontSize: 12, marginTop: 14 }}>{release.creator_name} · {new Date(release.published_at).toLocaleDateString()}</div>
            <div style={{ color: "#d8c19d", fontSize: 12, marginTop: 8 }}>{release.average_score?.toFixed(1) ?? "—"} / 10 · {release.rating_count} ratings</div>
          </div>
        </a>)}
      </div>
      {!loading && releases.length === 0 && <p style={{ color: "#99958e", marginTop: 40 }}>No public releases match those filters.</p>}
    </div>
  </main>;
}
