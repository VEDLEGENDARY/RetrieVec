import { Archive, BookOpenText, FileText, Menu, Search } from "lucide-react";
import type { Collection } from "./api";
import { Button, IconButton, StatusBadge, Surface } from "./ui";

export type Destination = "ask" | "sources" | "saved";
export const destinationLabels: Record<Destination, string> = {
  ask: "Ask",
  sources: "Sources",
  saved: "Saved research",
};

/** Presentation only: collection scope, consent and routing remain with the app. */
export function CollectionHeader({
  collection,
  busy,
  navigationOpen,
  onOpenNavigation,
  onArchive,
}: {
  collection?: Collection;
  busy: boolean;
  navigationOpen: boolean;
  onOpenNavigation: () => void;
  onArchive: () => void;
}) {
  return (
    <Surface as="header" material="glass" className="collection-header">
      <div className="collection-header-content">
        <div className="collection-heading">
          <IconButton
            className="mobile-menu"
            aria-label="Open navigation"
            aria-controls="workspace-navigation"
            aria-expanded={navigationOpen}
            onClick={onOpenNavigation}
          >
            <Menu aria-hidden="true" />
          </IconButton>
          <p className="eyebrow">Research workspace</p>
          <h1>{collection?.title ?? "A place for your next question"}</h1>
          {collection && (
            <div className="header-meta">
              <span>
                {collection.visibility === "curated"
                  ? "Curated collection"
                  : "Private collection"}
              </span>
              <StatusBadge
                tone={collection.active_snapshot ? "success" : "info"}
              >
                {collection.active_snapshot
                  ? "Search ready"
                  : "Awaiting sources"}
              </StatusBadge>
            </div>
          )}
        </div>
        {collection?.can_manage && (
          <Button
            variant="quiet"
            onClick={onArchive}
            disabled={busy}
            title="Hide this collection and cancel active processing. Undo restores access, but does not restart cancelled work."
          >
            <Archive aria-hidden="true" /> Archive collection
          </Button>
        )}
      </div>
    </Surface>
  );
}

export function WorkspaceDestinations({
  selected,
  onSelect,
}: {
  selected: Destination;
  onSelect: (destination: Destination) => void;
}) {
  return (
    <nav className="view-tabs" aria-label="Workspace sections">
      {(
        [
          ["ask", Search],
          ["sources", FileText],
          ["saved", BookOpenText],
        ] as const
      ).map(([destination, Icon]) => (
        <Button
          key={destination}
          className={selected === destination ? "active" : ""}
          aria-current={selected === destination ? "page" : undefined}
          onClick={() => onSelect(destination)}
        >
          <Icon aria-hidden="true" />
          {destinationLabels[destination]}
        </Button>
      ))}
    </nav>
  );
}
