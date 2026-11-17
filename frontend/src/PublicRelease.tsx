import { useEffect, useState } from "react";

type PublicReleaseData = {
  slug: string; title: string; synopsis: string; visibility: "public" | "unlisted";
  published_at: string; project_title: string; format: string | null;
  category: string | null; genre: string | null; duration_ms: number | null;
  width: number | null; height: number | null; video_url: string;
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

  const shell: React.CSSProperties = {
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
          <span style={{ color: "#a9a6a0", fontSize: 12, textTransform: "uppercase", letterSpacing: ".12em" }}>{release.visibility} release</span>
        </header>
        <div style={{ color: "#c9a77b", fontSize: 12, letterSpacing: ".18em", textTransform: "uppercase" }}>{release.genre || release.category || "A published work"}</div>
        <h1 style={{ fontSize: "clamp(38px, 7vw, 76px)", lineHeight: 1.02, margin: "14px 0 18px", maxWidth: 900 }}>{release.title}</h1>
        <p style={{ color: "#b7b3ad", fontSize: 15, margin: "0 0 28px" }}>
          {release.project_title}{release.format ? ` · ${release.format === "tv_series" ? "TV series" : "Film"}` : ""} · Published {new Date(release.published_at).toLocaleDateString()}
        </p>
        <video controls playsInline preload="metadata" style={{ width: "100%", maxHeight: "70vh", background: "#050505", borderRadius: 8, display: "block" }}>
          <source src={release.video_url} type="video/mp4" />
          Your browser does not support HTML video.
        </video>
        {release.synopsis && <section style={{ maxWidth: 760, marginTop: 42 }}><h2 style={{ fontSize: 22 }}>Synopsis</h2><p style={{ color: "#d0cdc7", lineHeight: 1.8, whiteSpace: "pre-wrap" }}>{release.synopsis}</p></section>}
        <footer style={{ borderTop: "1px solid #343438", marginTop: 64, paddingTop: 22, color: "#85827d", fontSize: 12 }}>Published with StoryForge · {release.slug}</footer>
      </div>
    </main>
  );
}
