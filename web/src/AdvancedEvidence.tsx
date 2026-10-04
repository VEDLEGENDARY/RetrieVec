import { ActionLink, Notice, LoadingState, Disclosure } from "./ui";
import { useEffect, useState } from "react";
import { api } from "./api";

type Cell = {
  row: number;
  column: number;
  row_span: number;
  column_span: number;
  text: string;
  role: string;
  unit: string | null;
  missing: boolean;
  ambiguous: boolean;
};
type Content =
  | { kind: "prose"; text: string }
  | {
      kind: "table";
      rows: number;
      columns: number;
      cells: Cell[];
      caption: string;
      footnotes: string[];
    }
  | {
      kind: "equation";
      transcription: string;
      label: string | null;
      definitions: string[];
    }
  | {
      kind: "figure";
      caption: string;
      observations: { text: string; basis: string; uncertain: boolean }[];
    };
type Evidence = {
  evidence_id: string;
  content: Content;
  derivation: string;
  review: { status: string };
  warnings: string[];
  raw_output: string;
  synthesis_allowed: boolean;
  locator: {
    page: number;
    display_box: [number, number, number, number];
    display_size: [number, number];
  };
};

function Structure({ content }: { content: Content }) {
  if (content.kind === "prose") return <blockquote>{content.text}</blockquote>;
  if (content.kind === "equation")
    return (
      <>
        <h4>{content.label ?? "Equation transcription"}</h4>
        <pre>{content.transcription}</pre>
        <p>Mathematical equivalence has not been verified.</p>
        <ul>
          {content.definitions.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      </>
    );
  if (content.kind === "figure")
    return (
      <>
        <p>{content.caption}</p>
        <p>Precise values are not established by these observations.</p>
        <ul>
          {content.observations.map((item, index) => (
            <li key={index}>
              {item.text} · {item.basis.replaceAll("_", " ")}{" "}
              {item.uncertain && "· uncertain"}
            </li>
          ))}
        </ul>
      </>
    );
  const rows = Math.min(content.rows, 50),
    columns = Math.min(content.columns, 20);
  const cells = new Map(
    content.cells.map((cell) => [`${cell.row}:${cell.column}`, cell]),
  );
  const covered = new Set<string>();
  for (const cell of content.cells) {
    for (
      let row = cell.row;
      row < Math.min(rows, cell.row + cell.row_span);
      row++
    ) {
      for (
        let column = cell.column;
        column < Math.min(columns, cell.column + cell.column_span);
        column++
      ) {
        if (row !== cell.row || column !== cell.column)
          covered.add(`${row}:${column}`);
      }
    }
  }
  return (
    <div className="advanced-table">
      {(rows < content.rows || columns < content.columns) && (
        <p>
          Partial table preview. Inspect the original page for the full table.
        </p>
      )}
      <table>
        <caption>{content.caption || "Extracted table"}</caption>
        <tbody>
          {Array.from({ length: rows }, (_, row) => (
            <tr key={row}>
              {Array.from({ length: columns }, (_, column) => {
                const key = `${row}:${column}`;
                if (covered.has(key)) return null;
                const cell = cells.get(key);
                if (!cell) return <td key={key}>Not extracted</td>;
                const Tag = cell.role === "data" ? "td" : "th";
                return (
                  <Tag
                    key={key}
                    rowSpan={Math.min(cell.row_span, rows - row)}
                    colSpan={Math.min(cell.column_span, columns - column)}
                  >
                    {cell.missing ? "Missing" : cell.text || "Empty"}
                    {cell.unit && ` (${cell.unit})`}
                    {cell.ambiguous && " · ambiguous"}
                  </Tag>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
      {content.footnotes.map((text, index) => (
        <p key={index}>{text}</p>
      ))}
    </div>
  );
}

export function AdvancedEvidence({
  collectionId,
  snapshotId,
  chunkId,
}: {
  collectionId: string;
  snapshotId: string;
  chunkId: string;
}) {
  const [value, setValue] = useState<Evidence | null>(null);
  const [error, setError] = useState("");
  const path = `/api/v1/collections/${encodeURIComponent(collectionId)}/snapshots/${encodeURIComponent(snapshotId)}/evidence/${encodeURIComponent(chunkId)}`;
  useEffect(() => {
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    setValue(null);
    setError("");
    async function refresh() {
      try {
        const result = await api<Evidence>(path, {
          signal: AbortSignal.any([
            controller.signal,
            AbortSignal.timeout(15000),
          ]),
        });
        if (controller.signal.aborted) return;
        setValue(result);
        timer = setTimeout(refresh, 5000);
      } catch {
        if (!controller.signal.aborted) {
          setValue(null);
          setError(
            "Evidence is unavailable or access changed. Select the result again to retry.",
          );
        }
      }
    }
    void refresh();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [path]);
  if (!value)
    return error ? (
      <Notice error>{error}</Notice>
    ) : (
      <LoadingState label="Loading retained source region…" />
    );
  const [x0, y0, x1, y1] = value.locator.display_box;
  const [width, height] = value.locator.display_size;
  return (
    <section
      aria-label="Structured source evidence"
      className="advanced-evidence"
    >
      <p>
        {value.content.kind} · {value.derivation.replaceAll("_", " ")} · review{" "}
        {value.review.status}
      </p>
      {!value.synthesis_allowed && (
        <p>
          Inspect this extraction before relying on it. It is excluded from
          answer generation.
        </p>
      )}
      <div className="advanced-page">
        <img
          src={`${path}/images/page`}
          alt={`Retained source page ${value.locator.page}`}
        />
        <svg
          viewBox={`0 0 ${width} ${height}`}
          preserveAspectRatio="none"
          role="img"
          aria-label="Highlighted evidence region"
        >
          <rect
            className="evidence-region-halo"
            x={x0}
            y={y0}
            width={x1 - x0}
            height={y1 - y0}
            fill="none"
          />
          <rect
            className="evidence-region"
            x={x0}
            y={y0}
            width={x1 - x0}
            height={y1 - y0}
            fill="none"
          />
        </svg>
      </div>
      <ActionLink
        href={`${path}/original#page=${value.locator.page}`}
        target="_blank"
        rel="noreferrer"
      >
        Compare original PDF page
      </ActionLink>
      <Structure content={value.content} />
      {value.warnings.length > 0 && (
        <ul>
          {value.warnings.map((text, index) => (
            <li key={index}>{text}</li>
          ))}
        </ul>
      )}
      <Disclosure>
        <summary>Raw extraction output</summary>
        <pre>{value.raw_output}</pre>
      </Disclosure>
    </section>
  );
}
