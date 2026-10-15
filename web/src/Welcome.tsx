import { BookOpenText, Files, Search, Quote, ShieldCheck } from "lucide-react";
import { ActionLink, Notice } from "./ui";
import { ThemeControl } from "./ThemeControl";

export function Welcome({ error }: { error: string }) {
  return (
    <main className="welcome research-welcome">
      <div className="welcome-brand wordmark">
        <span className="logo-mark">
          <BookOpenText size={20} aria-hidden="true" />
        </span>
        RetrieVec
        <span className="welcome-caption">
          Your papers. Traceable evidence.
        </span>
        <ThemeControl />
      </div>
      <div className="welcome-layout">
        <div className="welcome-copy">
          <p className="welcome-subject">
            <Files size={18} aria-hidden="true" /> A workspace for research
            papers
          </p>
          <h1>
            A reading room
            <br />
            for traceable evidence.
          </h1>
          <p className="intro">
            Search your papers, read the evidence, and save cited answers. Every
            answer traces to a passage; every passage stays tied to a source
            hash and an immutable snapshot.
          </p>
          <ActionLink variant="primary" href="/auth/login">
            Sign in to your workspace
          </ActionLink>
          <p className="welcome-signin-note">
            Using the local starter workspace? Choose Register on the sign-in
            screen.
          </p>
          {error && <Notice error>{error}</Notice>}
          <p className="welcome-privacy">
            <ShieldCheck size={17} aria-hidden="true" /> Private collections.
            Cloud generation only with your consent.
          </p>
        </div>
        <section
          className="welcome-preview"
          aria-label="Research workflow illustration"
        >
          <div className="preview-header">
            <BookOpenText size={18} aria-hidden="true" />
            <span>A question. A passage. A source.</span>
          </div>
          <div className="preview-question">
            <Search size={20} aria-hidden="true" />
            <p>What methods do these papers use?</p>
          </div>
          <div className="preview-paper">
            <span className="preview-paper-kind">Your paper</span>
            <h2>Methods &amp; findings</h2>
            <div className="paper-line" />
            <div className="paper-line short" />
            <div className="preview-highlight">
              <Quote size={20} aria-hidden="true" />
              <p>
                Find a relevant passage and follow it back to the original
                paper.
              </p>
            </div>
            <div className="paper-line" />
            <div className="paper-line short" />
            <div className="preview-citation">
              <BookOpenText size={16} aria-hidden="true" /> Original source kept
              with your evidence
            </div>
          </div>
          <p className="preview-caption">
            An illustration of your workflow. Your results come from the papers
            you add.
          </p>
        </section>
      </div>
      <ol className="welcome-flow">
        <li>
          <Files aria-hidden="true" />
          <div>
            <h2>Collect your papers</h2>
            <p>Organize PDFs and notes into a private collection.</p>
          </div>
        </li>
        <li>
          <Search aria-hidden="true" />
          <div>
            <h2>Follow the evidence</h2>
            <p>Search across papers and inspect the original passages.</p>
          </div>
        </li>
        <li>
          <Quote aria-hidden="true" />
          <div>
            <h2>Keep the citations</h2>
            <p>Shortlist evidence and export it for your writing.</p>
          </div>
        </li>
      </ol>
    </main>
  );
}
