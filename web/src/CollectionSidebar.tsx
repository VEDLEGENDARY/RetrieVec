import { useState, type SubmitEvent } from "react";
import { BookOpenText, X, Plus, ShieldCheck, LogOut } from "lucide-react";
import { Button, Input } from "./ui";
import type { Collection } from "./api";

export function CollectionSidebar({
  collections,
  selected,
  onSelect,
  onClose,
  title,
  setTitle,
  busy,
  create,
  logout,
}: {
  collections: Collection[];
  selected: string;
  onSelect: (id: string) => void;
  onClose: () => void;
  title: string;
  setTitle: (value: string) => void;
  busy: boolean;
  create: (event: SubmitEvent) => Promise<void>;
  logout: () => Promise<void>;
}) {
  const [collectionFilter, setCollectionFilter] = useState("");
  return (
    <>
      <div className="wordmark">
        <span className="logo-mark">
          <BookOpenText size={18} />
        </span>{" "}
        RetrieVec
        <Button
          className="mobile-close"
          aria-label="Close navigation"
          onClick={() => onClose()}
        >
          <X size={18} />
        </Button>
      </div>
      <div className="library-heading">
        <h2>Collections</h2>
        <span>{collections.length}</span>
      </div>
      <label className="collection-filter">
        Find a collection
        <Input
          type="search"
          value={collectionFilter}
          onChange={(event) => setCollectionFilter(event.target.value)}
          placeholder="Filter collections…"
        />
      </label>
      <nav aria-label="Collections">
        {collections
          .filter((item) =>
            item.title.toLowerCase().includes(collectionFilter.toLowerCase()),
          )
          .map((item) => (
            <Button
              key={item.collection_id}
              className={
                selected === item.collection_id
                  ? "collection selected"
                  : "collection"
              }
              aria-pressed={selected === item.collection_id}
              onClick={() => {
                onSelect(item.collection_id);
                onClose();
              }}
            >
              <span>{item.title}</span>
              <small>
                {item.visibility === "curated" ? "Curated" : "Private"}
              </small>
            </Button>
          ))}
      </nav>
      {collectionFilter &&
        !collections.some((item) =>
          item.title.toLowerCase().includes(collectionFilter.toLowerCase()),
        ) && (
          <p className="muted" role="status">
            No collections match “{collectionFilter}”.
          </p>
        )}
      <form onSubmit={create} className="new-collection">
        <label htmlFor="collection-title">New collection</label>
        <Input
          id="collection-title"
          value={title}
          onChange={(event) => setTitle(event.target.value)}
          maxLength={120}
          required
          placeholder="e.g. Retrieval methods"
        />
        <Button disabled={busy || !title.trim()} type="submit">
          <Plus size={16} /> Create collection
        </Button>
      </form>
      <div className="account">
        <span>
          <ShieldCheck size={14} /> Private workspace
        </span>
        <Button onClick={logout}>
          <LogOut size={14} /> Sign out
        </Button>
      </div>
    </>
  );
}
