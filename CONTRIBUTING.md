# Contributing to RetrieVec

`main` is protected integration history. Create a focused branch using `feat/`, `fix/`, `test/`, `perf/`, `docs/` or `chore/`; never develop or commit directly on `main`.

1. Describe one bounded change and its acceptance evidence.
2. Create or reuse the approved feature branch.
3. Preserve unrelated working-tree changes.
4. Implement commit-sized steps with conventional commit messages.
5. Run `python scripts/check.py` and relevant web, data, model or container checks.
6. Record only checks that actually ran and disclose incomplete human/model gates.
7. Push the branch and open a focused pull request.
8. Require CI and review, then merge with a merge commit. Do not squash history.

Commit synthetic fixtures, schemas and small golden records. Keep downloaded papers, credentials, `.env`, sessions, private judgments, model weights, backups and generated `artifacts/` out of Git. Preserve corpus/model/split provenance and never describe synthetic labels as human-reviewed evidence.

Keep dependencies pinned. Format Python with Ruff, Go with `gofmt`, and build the React production bundle before review. Any default retrieval or model change needs a direct comparison against the unchanged reference.
