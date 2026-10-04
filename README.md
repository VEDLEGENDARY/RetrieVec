<div align="center">

# RetrieVec

### Your papers. Clear evidence. Research you can trace.

A private research workspace that turns your papers into searchable passages and cited answers.

[Get started](#get-started) · [Explore the workflow](#from-paper-to-evidence) · [Measured results](BENCHMARKS.md) · [Developer guide](docs/DEVELOPMENT.md)

![Self-hosted](https://img.shields.io/badge/self--hosted-0f766e?style=flat-square)
![CPU retrieval](https://img.shields.io/badge/CPU-retrieval-334155?style=flat-square)
[![MIT License](https://img.shields.io/badge/license-MIT-334155?style=flat-square)](LICENSE)

</div>

![RetrieVec workspace showing collections, a research question, passage search, and an evidence shortlist](docs/images/workspace.png)

*The current interface with synthetic demo data. This preview is separate from benchmark evidence.*

## Find the passage behind the answer

Reading across a folder of papers takes time. RetrieVec brings your sources into one workspace so you can ask a question, inspect relevant passages, and keep the evidence worth returning to.

| Bring your sources | Follow an idea | Keep the evidence |
| :--- | :--- | :--- |
| Organize text and text-based PDFs into private collections. | Find passages by keywords and meaning, then open the source. | Shortlist excerpts, save research, and export it with source references. |

**Search works without an answer model.** When an operator configures generation, you can also request answers with citations and check them against the original passages.

## From paper to evidence

1. **Collect** — Create a collection and upload your sources. Review ingestion progress before searching.
2. **Ask** — Start with a focused question, such as “How does dense retrieval compare with lexical matching?”
3. **Inspect** — Read the returned passages, open their sources, and compare the evidence.
4. **Keep** — Build a shortlist, save the conversation, or export research for later use.

<details>
<summary><strong>A closer look at the workspace</strong></summary>

- **Source context:** Trace excerpts to their source and corpus snapshot.
- **Evidence shortlist:** Keep up to six excerpts together while researching a collection.
- **Saved research:** Return to conversations and export source references alongside your findings.
- **Comfortable reading:** Light and dark themes, responsive layouts, and keyboard navigation.
- **Retrieval controls:** Compare keyword, semantic, and hybrid search when you want to investigate ranking.

The active shortlist and recent searches are temporary and clear on reload or collection changes. Save or export the research you want to keep.

</details>

## Get started

RetrieVec is self-hosted. The container setup needs **Docker with Compose** and an **OpenID Connect sign-in provider**.

1. Copy [`.env.example`](.env.example) to `.env`.
2. Follow the [configuration steps](docs/DEVELOPMENT.md#docker-quick-start) to set credentials and register your sign-in callback.
3. Build and start the workspace:

   ```sh
   docker compose -f compose.app.yaml up --build -d
   ```

4. Open **http://127.0.0.1:8000**, sign in, and create your first collection.

For local development, follow the [Windows or Linux setup](docs/DEVELOPMENT.md#native-setup). The guide also covers a local Keycloak sign-in provider and optional answer generation.

## What has been measured?

RetrieVec includes reproducible retrieval evaluations on **SciFact and SCIDOCS**, with per-query results and paired confidence intervals. Those measurements cover retrieval; they do not establish the accuracy of generated answers.

The separate answer study uses **synthetic questions and automatic-only scoring**. Human review remains blank, and the NLI check was **not run**. Reranking and score blending remain opt-in experiments; defaults are unchanged.

[Retrieval results and limitations →](BENCHMARKS.md) · [Answer study and reranker diagnosis →](docs/results/answer-quality-stage-2.3.md)

## Go deeper

| Looking for… | Start here |
| :--- | :--- |
| Setup, architecture, and deployment | [Developer and operations guide](docs/DEVELOPMENT.md) |
| How the main user journeys work | [Core flows](CORE_FLOWS.md) |
| Retrieval measurements and reproduction | [Benchmarks](BENCHMARKS.md) |
| Performance notes | [Performance guide](PERF.md) |
| Answer evaluation and experimental reranking | [Stage 2.3 findings](docs/results/answer-quality-stage-2.3.md) |

Built with **React · Python · Go · PostgreSQL**. Released under the [MIT License](LICENSE).
