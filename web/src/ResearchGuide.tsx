import { BookOpenText, Check, Files, HelpCircle, Search } from "lucide-react";
import { useRef } from "react";
import { Button, Disclosure, IconButton, NativeDialog } from "./ui";
import type { Collection } from "./api";
import type { Destination } from "./WorkspaceChrome";

export function CollectionJourney({
  collection,
  onSelect,
}: {
  collection: Collection;
  onSelect: (destination: Destination) => void;
}) {
  return (
    <nav className="collection-journey" aria-label="Research workflow">
      <span className="journey-intro">Your next step</span>
      <Button
        className={
          collection.active_snapshot ? "journey-complete" : "journey-current"
        }
        onClick={() => onSelect("sources")}
      >
        {collection.active_snapshot ? (
          <Check aria-hidden="true" />
        ) : (
          <Files aria-hidden="true" />
        )}
        <span>
          Add papers
          <small>
            {collection.active_snapshot
              ? "Searchable collection"
              : "PDFs, text and notes"}
          </small>
        </span>
      </Button>
      <Button
        className={collection.active_snapshot ? "journey-current" : ""}
        onClick={() => onSelect("ask")}
      >
        <Search aria-hidden="true" />
        <span>
          Find evidence<small>Ask a research question</small>
        </span>
      </Button>
      <Button onClick={() => onSelect("saved")}>
        <BookOpenText aria-hidden="true" />
        <span>
          Return to research<small>Saved answers and exports</small>
        </span>
      </Button>
    </nav>
  );
}

export function ResearchGuide() {
  const dialog = useRef<HTMLDialogElement>(null);
  const trigger = useRef<HTMLButtonElement>(null);
  return (
    <>
      <Button
        ref={trigger}
        variant="quiet"
        className="guide-trigger"
        onClick={() => dialog.current?.showModal()}
      >
        <HelpCircle size={17} aria-hidden="true" /> Research guide
      </Button>
      <NativeDialog
        ref={dialog}
        className="research-guide"
        aria-labelledby="guide-heading"
        onClose={() => trigger.current?.focus()}
      >
        <div className="guide-header">
          <div>
            <p className="muted">Getting started with RetrieVec</p>
            <h2 id="guide-heading">A paper to evidence workflow</h2>
          </div>
          <IconButton
            aria-label="Close research guide"
            onClick={() => dialog.current?.close()}
          >
            <span aria-hidden="true">×</span>
          </IconButton>
        </div>
        <ol className="guide-steps">
          <li>
            <h3>Create a collection</h3>
            <p>
              Use the sidebar to group papers by project, topic, or literature
              review. Your collections are private; curated starter collections
              are available for practice.
            </p>
          </li>
          <li>
            <h3>Add your papers in Sources</h3>
            <p>
              Drop up to 10 PDF, text, or Markdown files, review the selection,
              then choose Upload documents. Each file can be up to 25 MiB; PDFs
              can have up to 100 pages. Wait for processing to finish.
            </p>
          </li>
          <li>
            <h3>Ask a specific question</h3>
            <p>
              Use Find passages to search immediately. Ask about a method,
              finding, or limitation. Open a result to inspect the full passage
              and its source; shortlist useful passages.
            </p>
          </li>
          <li>
            <h3>Save and export your evidence</h3>
            <p>
              Export your passage shortlist from More evidence options. If an
              answer provider is configured, use Answer for cited responses,
              then return to Saved research to inspect citations and export
              Markdown, BibTeX, JSON, or CSV.
            </p>
          </li>
        </ol>
        <Disclosure>
          <summary>PDFs, privacy, and answer availability</summary>
          <p>
            Upload unencrypted PDFs with selectable text. Scanned pages need OCR
            before uploading. Paper filenames are retained as titles; check the
            original paper before using a citation.
          </p>
          <p>
            Passage search needs no generation provider. Local or cloud answers
            need a separately configured provider. Cloud providers require
            explicit consent for each collection.
          </p>
          <p>
            Retrieval scores describe ranking. They do not establish scientific
            validity or factual support.
          </p>
        </Disclosure>
        <div className="guide-shortcuts">
          <span>
            <kbd>Ctrl / ⌘ K</kbd> Quick actions
          </span>
          <span>
            <kbd>Ctrl / ⌘ Enter</kbd> Submit a question
          </span>
          <span>
            <kbd>Esc</kbd> Close an inspector or dialog
          </span>
        </div>
        <Button variant="primary" onClick={() => dialog.current?.close()}>
          Back to my research
        </Button>
      </NativeDialog>
    </>
  );
}
