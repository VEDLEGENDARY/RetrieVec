import type { ReactNode } from "react";
import { Disclosure } from "./ui";

export type EvidenceEntry = { id: string; content: ReactNode };

/** Actual returned passages and actual cited IDs; never treats the shortlist as citations. */
export function BasedOn({
  kind,
  candidates,
  usedIds = [],
  snapshot,
  model,
}: {
  kind: "search" | "answer";
  candidates: EvidenceEntry[];
  usedIds?: string[];
  snapshot: string;
  model?: string;
}) {
  const unique = [
    ...new Map(candidates.map((item) => [item.id, item])).values(),
  ];
  const used = new Set(usedIds);
  const cited = unique.filter((item) => used.has(item.id));
  const remaining = unique.filter((item) => !used.has(item.id));
  const list = (items: EvidenceEntry[]) => (
    <ul>
      {items.map((item) => (
        <li key={item.id}>{item.content}</li>
      ))}
    </ul>
  );
  return (
    <Disclosure
      className="based-on"
      id={kind === "answer" ? "answer-based-on" : "search-based-on"}
    >
      <summary>
        {kind === "answer"
          ? `Based on ${cited.length} cited ${cited.length === 1 ? "passage" : "passages"} · ${unique.length} retrieved ${unique.length === 1 ? "candidate" : "candidates"}`
          : `Based on ${unique.length} retrieved ${unique.length === 1 ? "passage" : "passages"}`}
      </summary>
      {kind === "answer" ? (
        <>
          <h4>Used in claims or comparisons</h4>
          {cited.length ? (
            list(cited)
          ) : (
            <p>No retained passages are cited by this answer.</p>
          )}
          <h4>Retrieved but not cited</h4>
          {remaining.length ? (
            list(remaining)
          ) : (
            <p>No additional retained candidates.</p>
          )}
          <p>
            Counts cover the retained evidence pool. Citations identify use, not
            scientific validity.
          </p>
        </>
      ) : (
        <>
          <p>
            Returned search passages, not evidence used by a generated answer.
          </p>
          {list(unique)}
        </>
      )}
      <p>
        Snapshot: <code>{snapshot}</code>
        {model && <> · Model: {model}</>}
      </p>
      <p>
        The evidence shortlist is your temporary selection and does not
        determine an answer’s citations.
      </p>
    </Disclosure>
  );
}
