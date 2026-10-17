import { useId, useMemo, useState } from "react";
import { ArrowDown, ArrowUp, ArrowUpDown, BookOpenText } from "lucide-react";
import { ActionLink, Button, Disclosure } from "../../ui";
import { ThemeControl } from "../../ThemeControl";
import { benchmark } from "./data";
import type { BenchmarkRow, Dataset, Pipeline } from "./types";
import "./results.css";

const datasets: Record<Dataset, string> = {
  scifact: "SciFact",
  scidocs: "SCIDOCS",
};
const pipelines: Record<Pipeline, string> = {
  default_sparse: "Default sparse",
  default_dense: "Default dense",
  default_hybrid: "Default hybrid",
  tuned_sparse: "Selected sparse",
  tuned_hybrid: "Selected hybrid",
};
const columns = [
  ["dataset", "Dataset"],
  ["pipeline", "Pipeline"],
  ["ndcg10", "nDCG@10"],
  ["recall100", "Recall@100"],
  ["mrr10", "MRR@10"],
  ["p50", "p50 ms"],
  ["p95", "p95 ms"],
] as const;
type SortKey = (typeof columns)[number][0];
function QualityLatency() {
  const title = useId(),
    description = useId();
  const labels = [...benchmark.rows].sort(
    (a, b) => a.dataset.localeCompare(b.dataset) || b.ndcg10 - a.ndcg10,
  );
  const width = 1100,
    height = 600,
    left = 70,
    right = 720,
    top = 40,
    bottom = 530;
  const x = (value: number) => left + (value / 1300) * (right - left);
  const y = (value: number) => bottom - (value / 0.75) * (bottom - top);
  return (
    <figure className="benchmark-figure">
      <figcaption>Quality and warm retrieval latency</figcaption>
      <p>
        One point for each dataset and pipeline. Labels connect directly to
        their points. The table gives the same values.
      </p>
      <div
        className="scatter-scroll"
        role="region"
        aria-label="Quality and latency scatter plot"
        tabIndex={0}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-labelledby={`${title} ${description}`}
        >
          <title id={title}>nDCG@10 against p50 retrieval latency</title>
          <desc id={description}>
            {benchmark.rows
              .map(
                (row) =>
                  `${datasets[row.dataset]}, ${pipelines[row.pipeline]}: nDCG@10 ${row.ndcg10.toFixed(4)}, p50 ${row.p50.toFixed(2)} milliseconds.`,
              )
              .join(" ")}
          </desc>
          {[0, 0.15, 0.3, 0.45, 0.6, 0.75].map((tick) => (
            <g key={tick}>
              <line
                className="scatter-grid"
                x1={left}
                x2={right}
                y1={y(tick)}
                y2={y(tick)}
              />
              <text
                className="scatter-metric"
                x={left - 12}
                y={y(tick) + 5}
                textAnchor="end"
              >
                {tick.toFixed(2)}
              </text>
            </g>
          ))}
          {[0, 250, 500, 750, 1000, 1250].map((tick) => (
            <g key={tick}>
              <line
                className="scatter-grid"
                x1={x(tick)}
                x2={x(tick)}
                y1={top}
                y2={bottom}
              />
              <text
                className="scatter-metric"
                x={x(tick)}
                y={bottom + 25}
                textAnchor="middle"
              >
                {tick}
              </text>
            </g>
          ))}
          <text x={left} y={20}>
            nDCG@10
          </text>
          <text x={(left + right) / 2} y={height - 12} textAnchor="middle">
            p50 latency (ms)
          </text>
          {labels.map((row, index) => {
            const sameDatasetIndex = labels
              .slice(0, index)
              .filter((item) => item.dataset === row.dataset).length;
            const labelY =
              (row.dataset === "scifact" ? 62 : 350) + sameDatasetIndex * 38;
            return (
              <g
                key={`${row.dataset}:${row.pipeline}`}
                className={`dataset-${row.dataset}`}
                data-point={`${row.dataset}:${row.pipeline}`}
              >
                <path
                  className="scatter-connector"
                  d={`M ${x(row.p50)} ${y(row.ndcg10)} L 738 ${labelY - 4} L 754 ${labelY - 4}`}
                />
                <circle
                  className="scatter-point"
                  cx={x(row.p50)}
                  cy={y(row.ndcg10)}
                  r={row.pipeline.startsWith("tuned") ? 4 : 6}
                />
                <text className="scatter-label" x={762} y={labelY}>
                  {datasets[row.dataset]}: {pipelines[row.pipeline]}
                </text>
              </g>
            );
          })}
        </svg>
      </div>
    </figure>
  );
}
export function ResultsPage() {
  const [sort, setSort] = useState<{ key: SortKey; descending: boolean }>({
    key: "dataset",
    descending: false,
  });
  const rows = useMemo(
    () =>
      [...benchmark.rows].sort((a, b) => {
        const left = a[sort.key],
          right = b[sort.key];
        const difference =
          typeof left === "number" && typeof right === "number"
            ? left - right
            : String(left).localeCompare(String(right));
        return (
          (sort.descending ? -difference : difference) ||
          a.pipeline.localeCompare(b.pipeline)
        );
      }),
    [sort],
  );
  return (
    <main className="results-page" id="results-main">
      <a className="skip" href="#benchmark-table">
        Skip to benchmark table
      </a>
      <header className="results-header">
        <ActionLink href="/" className="results-home">
          <BookOpenText aria-hidden="true" />
          RetrieVec workspace
        </ActionLink>
        <ThemeControl />
      </header>
      <div className="results-intro">
        <h1>Retrieval results</h1>
        <p>
          A measured view of ranking quality and warm local latency. These are
          the results recorded on{" "}
          <time dateTime={benchmark.date}>October 1, 2026</time>.
        </p>
      </div>
      <div className="results-layout">
        <section aria-labelledby="benchmark-heading">
          <h2 id="benchmark-heading">Held-out retrieval benchmarks</h2>
          <p>
            SciFact uses 300 test queries and 5,183 papers. SCIDOCS uses 1,000
            test queries and 25,657 papers. Selected parameters come from
            SciFact development queries.
          </p>
          <div
            className="benchmark-scroll"
            tabIndex={0}
            role="region"
            aria-label="Sortable retrieval benchmark results"
          >
            <table id="benchmark-table">
              <caption>
                October 1 benchmark. Quality scores use a 0 to 1 scale.
                Latencies are warm retrieval milliseconds. Activate a column
                header to sort.
              </caption>
              <thead>
                <tr>
                  {columns.map(([key, label]) => (
                    <th
                      key={key}
                      scope="col"
                      aria-sort={
                        sort.key === key
                          ? sort.descending
                            ? "descending"
                            : "ascending"
                          : "none"
                      }
                    >
                      <Button
                        onClick={() =>
                          setSort({
                            key,
                            descending:
                              sort.key === key ? !sort.descending : false,
                          })
                        }
                        aria-label={`Sort by ${label}`}
                      >
                        {label}
                        {sort.key === key ? (
                          sort.descending ? (
                            <ArrowDown aria-hidden="true" />
                          ) : (
                            <ArrowUp aria-hidden="true" />
                          )
                        ) : (
                          <ArrowUpDown aria-hidden="true" />
                        )}
                      </Button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {rows.map((row: BenchmarkRow) => (
                  <tr
                    key={`${row.dataset}:${row.pipeline}`}
                    data-dataset={row.dataset}
                    data-pipeline={row.pipeline}
                  >
                    <th scope="row">{datasets[row.dataset]}</th>
                    <td>{pipelines[row.pipeline]}</td>
                    <td className="metric">{row.ndcg10.toFixed(4)}</td>
                    <td className="metric">{row.recall100.toFixed(4)}</td>
                    <td className="metric">{row.mrr10.toFixed(4)}</td>
                    <td className="metric">{row.p50.toFixed(2)}</td>
                    <td className="metric">{row.p95.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="results-sort-state" role="status">
            Sorted by {columns.find(([key]) => key === sort.key)?.[1]},{" "}
            {sort.descending ? "descending" : "ascending"}.
          </p>
          <QualityLatency />
        </section>
        <aside
          className="benchmark-limitations"
          aria-labelledby="limitations-heading"
        >
          <h2 id="limitations-heading">What these numbers mean</h2>
          <ul>
            <li>
              Paper-level ranking is collapsed from the top 100 retrieved
              chunks. Recall@100 is limited to that chunk pool.
            </li>
            <li>
              Latency measures warm local retrieval. It excludes HTTP,
              authorization, and database work.
            </li>
            <li>
              SCIDOCS uses SciFact-selected parameters unchanged. Its test
              queries were not used for tuning.
            </li>
            <li>
              No model was trained. The benchmark uses the pinned, pretrained
              MiniLM embedding model.
            </li>
            <li>
              These are title and abstract corpora. No answer quality or PDF
              extraction evaluation is included.
            </li>
            <li>
              Opt-in lossless wordpiece refinement differs from the default PDF
              upload chunking.
            </li>
            <li>
              These measurements do not establish general superiority,
              statistical significance, or semantic correctness.
            </li>
          </ul>
          <p>
            The README reports a later October 5 run. This page stays pinned to
            the October 1 JSON and does not mix those measurements.
          </p>
          <Disclosure>
            <summary>Benchmark identities and protocol</summary>
            <p>
              Source <code>{benchmark.source}</code> (stored compressed in the
              repository).
            </p>
            <p>
              Source SHA-256 <code>{benchmark.sourceSha256}</code>
            </p>
            {benchmark.corpora.map((corpus) => (
              <p key={corpus.dataset}>
                {datasets[corpus.dataset]} snapshot{" "}
                <code>{corpus.snapshot}</code>
              </p>
            ))}
            <p>{benchmark.protocol.documentRanking}</p>
            <p>{benchmark.protocol.latency}</p>
            <p>{benchmark.protocol.transfer}</p>
          </Disclosure>
        </aside>
      </div>
      <footer>
        Retrieval results describe ranking on these datasets. Read the source
        evidence before drawing a research conclusion.
      </footer>
    </main>
  );
}
