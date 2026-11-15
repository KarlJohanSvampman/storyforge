import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
  service: string;
  version: string;
};

type ApiState =
  | { status: "checking" }
  | { status: "online"; data: HealthResponse }
  | { status: "offline"; message: string };

export default function App() {
  const [api, setApi] = useState<ApiState>({ status: "checking" });

  useEffect(() => {
    const controller = new AbortController();

    fetch("/api/v1/health", { signal: controller.signal })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error("API returned HTTP " + response.status);
        }
        return (await response.json()) as HealthResponse;
      })
      .then((data) => setApi({ status: "online", data }))
      .catch((error: unknown) => {
        if (error instanceof DOMException && error.name === "AbortError") return;
        setApi({
          status: "offline",
          message: error instanceof Error ? error.message : "Unknown connection error",
        });
      });

    return () => controller.abort();
  }, []);

  return (
    <main className="page-shell">
      <header className="topbar">
        <a className="brand" href="/" aria-label="StoryForge home">
          <span className="brand-mark">S</span>
          <span>STORYFORGE <span className="brand-muted">COLLECTIVE</span></span>
        </a>
        <span className="topbar-label">Collaborative creative workspace</span>
      </header>

      <section className="hero" aria-labelledby="hero-title">
        <p className="eyebrow">MANY MINDS. MANY STORIES.</p>
        <h1 id="hero-title">Build something<br /><em>worth telling.</em></h1>
        <p className="hero-copy">
          A shared space to develop stories together and, over time, turn them
          into productions shaped by the whole team.
        </p>
        <div className="status-card" role="status" aria-live="polite">
          <span className={"status-indicator " + api.status} />
          <div>
            <strong>
              {api.status === "checking" && "Checking API connection"}
              {api.status === "online" && "Backend connected"}
              {api.status === "offline" && "Backend unavailable"}
            </strong>
            <p>
              {api.status === "checking" && "Waiting for the StoryForge API…"}
              {api.status === "online" && (api.data.service + " · v" + api.data.version)}
              {api.status === "offline" && api.message}
            </p>
          </div>
        </div>
      </section>

      <footer className="footer">
        <span>STORYFORGE COLLECTIVE</span>
        <span>Incremental build · Foundation 0.1</span>
      </footer>
    </main>
  );
}
