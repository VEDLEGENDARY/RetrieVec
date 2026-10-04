import { BookOpenText, Files, Search, Quote, ShieldCheck } from "lucide-react";

export function Welcome({ error }: { error: string }) {
  return (
    <main className="welcome welcome-layout">
      <div className="welcome-copy">
        <div className="wordmark">
          <span className="logo-mark">
            <BookOpenText aria-hidden="true" />
          </span>
          RetrieVec
        </div>
        <h1>
          Research begins
          <br />
          with the source.
        </h1>
        <p className="intro">
          Bring your papers together. Follow a question through the evidence,
          and keep the original source within reach.
        </p>
        <a className="button primary" href="/auth/login">
          Sign in to your workspace
        </a>
        {error && (
          <p role="alert" className="error">
            {error}
          </p>
        )}
        <p className="welcome-privacy">
          <ShieldCheck size={18} aria-hidden="true" />
          Your collections stay private.
        </p>
      </div>
      <section className="welcome-guide" aria-label="From papers to evidence">
        <div className="guide-heading">
          <BookOpenText aria-hidden="true" />
          <h2>Keep the evidence close.</h2>
        </div>
        <ol>
          <li>
            <Files aria-hidden="true" />
            <div>
              <h3>Build your reading collection</h3>
              <p>Add PDFs, text, and Markdown around a research question.</p>
            </div>
          </li>
          <li>
            <Search aria-hidden="true" />
            <div>
              <h3>Find the passage that matters</h3>
              <p>Search across your sources and compare relevant excerpts.</p>
            </div>
          </li>
          <li>
            <Quote aria-hidden="true" />
            <div>
              <h3>Trace every cited claim</h3>
              <p>
                Inspect the supporting passage before taking an answer forward.
              </p>
            </div>
          </li>
        </ol>
        <p className="guide-note">
          A retrieval score helps rank a passage. The source is where you verify
          it.
        </p>
      </section>
    </main>
  );
}
