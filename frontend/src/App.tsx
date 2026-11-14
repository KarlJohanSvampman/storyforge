import { useEffect, useState } from "react";
import {
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  Clapperboard,
  Compass,
  Film,
  Lightbulb,
  Plus,
  Sparkles,
  Users,
} from "lucide-react";

type ApiHealth = {
  status: string;
  service: string;
  version: string;
};

const phases = [
  { number: "01", title: "Story contributions", detail: "Bring your first ideas to the table.", icon: BookOpen, state: "active" },
  { number: "02", title: "Develop the story", detail: "Discuss, combine and shape the narrative.", icon: Lightbulb, state: "upcoming" },
  { number: "03", title: "Storyboard", detail: "Turn the story into scenes.", icon: Clapperboard, state: "upcoming" },
  { number: "04", title: "Bring it to life", detail: "Cast, perform, direct and edit.", icon: Film, state: "upcoming" },
];

function App() {
  const [health, setHealth] = useState<ApiHealth | null>(null);
  const [apiError, setApiError] = useState(false);

  useEffect(() => {
    fetch("/api/health")
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json() as Promise<ApiHealth>;
      })
      .then(setHealth)
      .catch(() => setApiError(true));
  }, []);

  return (
    <main className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label="StoryForge home">
          <span className="brand-mark"><Sparkles size={20} /></span>
          <span className="brand-name">storyforge<span>.</span></span>
        </a>

        <div className="workspace-label">YOUR WORKSPACE</div>
        <nav className="side-nav" aria-label="Main navigation">
          <a className="nav-item selected" href="#overview"><Compass size={17} /> Overview</a>
          <a className="nav-item" href="#projects"><BookOpen size={17} /> My projects</a>
          <a className="nav-item" href="#community"><Users size={17} /> Community</a>
        </nav>

        <div className="sidebar-bottom">
          <div className="collective-card">
            <div className="collective-icon"><Sparkles size={16} /></div>
            <div>
              <strong>The StoryForge Collective</strong>
              <span>Many minds. Many stories.</span>
            </div>
          </div>
          <div className="profile-row">
            <div className="avatar">S</div>
            <div className="profile-copy"><strong>Storyteller</strong><span>Creative member</span></div>
            <span className="profile-dots">···</span>
          </div>
        </div>
      </aside>

      <section className="main-panel" id="overview">
        <header className="topbar">
          <div className="breadcrumb">Workspace <span>/</span> Overview</div>
          <div className="topbar-right">
            <span className="beta-pill">EARLY ACCESS</span>
            <div className="avatar small">S</div>
          </div>
        </header>

        <div className="content">
          <section className="welcome">
            <div className="eyebrow"><span className="eyebrow-line" /> THE CREATIVE COLLECTIVE</div>
            <h1>Every great story<br /><em>starts together.</em></h1>
            <p className="welcome-copy">A space to bring ideas together, build worlds with others, and turn shared stories into something worth watching.</p>
            <div className="welcome-actions">
              <button className="primary-button" type="button" disabled><Plus size={17} /> Create a project <span className="soon-label">COMING NEXT</span></button>
              <a className="text-link" href="#journey">Explore the process <ArrowUpRight size={15} /></a>
            </div>
          </section>

          <section className="journey-section" id="journey">
            <div className="section-heading">
              <div><div className="section-kicker">HOW IT WORKS</div><h2>From first thought to final frame.</h2></div>
              <span className="step-count">A creative journey <span>·</span> 4 stages</span>
            </div>
            <div className="phase-grid">
              {phases.map((phase) => {
                const Icon = phase.icon;
                return (
                  <article className={`phase-card ${phase.state}`} key={phase.number}>
                    <div className="phase-top"><span>{phase.number}</span><Icon size={19} /></div>
                    <h3>{phase.title}</h3>
                    <p>{phase.detail}</p>
                    <div className="phase-status">{phase.state === "active" ? <><span className="status-dot" /> FIRST MILESTONE</> : "ON THE ROADMAP"}</div>
                  </article>
                );
              })}
            </div>
          </section>

          <section className="bottom-grid">
            <div className="note-card">
              <div className="note-icon"><Sparkles size={18} /></div>
              <div><div className="section-kicker">THE IDEA</div><h3>Many minds. Many stories. Endless interpretations.</h3><p>One shared starting point can lead to a hundred different creative directions. That's the heart of StoryForge.</p></div>
            </div>
            <div className="connection-card">
              <div className="connection-heading"><span className={health ? "connection-light online" : "connection-light"} /> DEVELOPMENT STATUS</div>
              <strong>{health ? "Backend connected" : apiError ? "Backend unavailable" : "Connecting to backend…"}</strong>
              <p>{health ? `${health.service} · v${health.version}` : apiError ? "Start the Docker services to connect the application." : "Checking the StoryForge API."}</p>
              {health && <div className="connected-label"><CheckCircle2 size={14} /> All systems operational</div>}
            </div>
          </section>

          <footer className="footer"><span>STORYFORGE COLLECTIVE</span><span>Built together, one story at a time.</span></footer>
        </div>
      </section>
    </main>
  );
}

export default App;
