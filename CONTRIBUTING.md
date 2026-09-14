# Contributing

Main is protected integration history. Do not develop or commit directly on main.

1. Prepare an issue describing one planned capability and its acceptance checks.
2. Obtain owner approval for a descriptive feature branch before creating it.
   Use prefixes such as `chore/`, `feat/`, `fix/`, `test/`, or `docs/`.
3. Implement one commit-sized step on that branch and update
   `docs/IMPLEMENTATION_STATUS.md` with validation evidence.
4. Run `scripts/check.py` using the installed development environment.
5. Show the diff and checks to the owner, and obtain explicit approval before
   committing. Use the planned conventional commit message where applicable.
6. Open a focused pull request linked to the issue. Require passing CI and owner
   review before merging through the pull request. Never push directly to main.

Keep all 14 milestone commits visible; do not squash the whole milestone.
For a step's own status entry, use "pending owner-approved commit" before it is
committed. Record its actual hash in the next status update or follow-up commit;
a commit cannot contain its own hash. Record CI evidence after an actual run.
Do not mark unrun gates as passed.

Commit synthetic fixtures, source manifests, and concise reports. Keep private
papers under `private/` and generated snapshots/results under `artifacts/`.
Never commit credentials, downloaded PDFs, private full text, or large outputs.
Do not change repository visibility without owner approval.

Configure repository rules to block direct main updates and require the
`checks (ubuntu-latest)` and `checks (windows-latest)` CI checks plus review.
The workflow file does not itself enable repository protection.
