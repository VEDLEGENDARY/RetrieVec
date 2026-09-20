# RetrieVec Engineering Workflow

This policy governs every plan and implementation milestone. Read it before changing the repository. If a repository-level contribution guide or branch-protection rule is stricter, follow the stricter rule.

## Approval boundaries

Work on one commit-sized task at a time.

1. Read the complete applicable plan, prerequisite plans, repository instructions, and implementation status when present. The first implementation task creates the status file if it does not exist.
2. Inspect the current branch, working tree, recent history, and relevant code. Preserve unrelated work.
3. Propose a branch name, scope, acceptance checks, and intended commit message. Obtain owner approval before creating or switching to the branch.
4. Implement only the approved task. Include its tests and directly necessary documentation.
5. Run the relevant checks. Present the diff summary, test results, known limitations, branch name, and exact proposed commit message.
6. Obtain explicit approval before committing. Branch approval does not authorize a commit.
7. Obtain separate approval before pushing, opening/updating a pull request, or merging unless the owner already authorized that exact action.
8. After the task is recorded, obtain approval before starting the next commit-sized task.

An approval applies only to the stated action and scope. Do not interpret approval for one branch, commit, or pull request as permission for later steps.

## Protected integration branch

Treat `main` or `master` as protected.

- Do not implement, commit, amend, rebase, reset, force-push, or resolve feature work directly on it.
- Start feature branches from an up-to-date integration branch after confirming the working tree is safe.
- Integrate through a pull request with required checks passing.
- Do not bypass reviews or branch protection to save time.
- Never rewrite shared history without explicit owner approval and a recovery plan.
- If work is accidentally started on the integration branch, stop before committing. Preserve the changes and ask how the owner wants them moved to an approved branch.

## Branch naming

Use short lowercase names describing the outcome:

```text
feat/corpus-snapshots
fix/segment-checksum-validation
test/snapshot-recovery
docs/retrieval-contracts
chore/ci-toolchain
perf/postings-decoder
refactor/search-boundaries
```

Rules:

- Use one category and a concise kebab-case subject.
- Name the behavior or subsystem, not the person or tool that produced it.
- Avoid dates, issue-free generic names such as `updates`, and marketing language.
- Never put credentials, customer/user data, experiment results, or ticket secrets in a branch name.
- Keep one coherent change stream per branch. Create another branch when the purpose changes materially.

## Commit construction

A commit is a reviewable, buildable unit with one reason to change.

- Include implementation, focused tests, migrations/contracts, and directly necessary docs together when they form one atomic behavior change.
- Do not mix formatting sweeps, dependency upgrades, generated artifacts, refactors, and product behavior unless inseparable.
- Stage by explicit path or interactive hunk selection. Do not use broad staging without reviewing every included file.
- Inspect `git diff`, `git diff --cached`, `git diff --cached --stat`, and `git diff --check` before requesting commit approval.
- Confirm new files are intentional and generated/private artifacts are ignored.
- Run the narrowest relevant checks first, then the repository's required pre-commit/CI checks.
- Never commit secrets, local environment files, downloaded private papers, build output, caches, model weights, large run artifacts, editor files, or credentials.
- Do not commit commented-out alternatives, debug prints, placeholder implementations, failing tests, or unexplained snapshots.
- Keep reproducible small fixtures in Git. Store large artifacts externally and commit manifests, hashes, generation commands, and concise reports.
- Update dependency locks with their manifest change. Review transitive changes and licenses.
- Schema and protocol changes include migrations, compatibility tests, and documentation in the same logical change.
- Do not amend an approved commit after its content changes without showing the new diff and obtaining fresh approval.

Temporary local commits are not part of this workflow unless the owner explicitly approves them. Do not create hidden checkpoint or `WIP` commits.

## Commit messages

Use Conventional Commit structure where it accurately describes the repository:

```text
type(optional-scope): imperative summary

Optional body explaining why the change is needed, important behavior,
tradeoffs, migration impact, and validation that will help future readers.

Optional issue or breaking-change footer.
```

Allowed types: `feat`, `fix`, `test`, `docs`, `refactor`, `perf`, `chore`, `build`, `ci`, `revert`.

Message rules:

- Write an imperative subject describing the result: `feat(index): persist compressed postings`.
- Keep the subject specific and normally under 72 characters; omit a period.
- Use a scope only when it improves navigation (`index`, `api`, `worker`, `ui`, `eval`).
- Explain motivation and observable behavior in the body; do not narrate file-by-file editing.
- State breaking changes through `BREAKING CHANGE:` and include the migration path.
- Reference a real issue only when one exists.
- Avoid vague subjects such as `update code`, `misc fixes`, `final changes`, or `improvements`.
- Do not include tool/vendor attribution, generation notices, promotional language, or fabricated co-author/reviewer trailers.
- Use the owner's configured Git identity. Never impersonate another contributor or claim independent review that did not occur.

Examples:

```text
feat(index): write deterministic segment files
fix(worker): reject stale ingestion leases
test(search): cover nested negation and repeated phrases
docs(architecture): define snapshot activation protocol
```

## Code and test style

Code should look like one coherent project maintained by thoughtful engineers.

- Follow the repository formatter, linter, naming conventions, package layout, and language idioms. Do not create a second style inside one codebase.
- Organize files around responsibilities and domain concepts. Avoid generic dumping grounds such as `helpers`, `utils`, or `common` unless their boundary is precise.
- Prefer direct implementations over speculative abstractions. Extract an interface when there are real implementations, a test boundary, or a documented near-term need.
- Keep functions cohesive and names concrete. Do not split simple logic into many one-line wrappers merely to appear modular.
- Use comments for invariants, intent, protocol details, numerical choices, security boundaries, and non-obvious tradeoffs. Do not restate the code.
- Avoid decorative section banners, tutorial narration, repetitive docstrings, fake quotations, conversational comments, and comments about how code was produced.
- Public APIs receive concise documentation required by their language/tooling. Private obvious functions do not need boilerplate comments.
- Errors should add useful operation/context while preserving typed causes where applicable. Never log secrets or private source text.
- Validate at boundaries; keep core domain logic deterministic where practical.
- Use `TODO(issue-number): reason` only for accepted deferred work. Do not leave anonymous TODOs as substitutes for implementation.
- Tests should describe behavior and failure conditions. Prefer small meaningful fixtures and independent expected values over mirroring implementation logic.
- Keep production code free of test-only branches; inject dependencies through deliberate seams.
- Run formatters mechanically. Keep pure formatting changes separate when they affect unrelated code.

Natural engineering style means consistent intent, concise naming, and evidence-backed decisions. It does not permit fabricated authorship, fake review history, deliberately degraded code, or evasion of a school, employer, competition, or repository disclosure policy.

## Pull requests

Open a pull request only after owner approval to push/open it.

The title should describe the final behavior and normally match the primary commit. The description should contain:

```text
Problem
Resulting behavior
Design/compatibility notes
Validation performed
Risks and limitations
Related issue/ADR
```

- Keep PRs small enough to review in one focused session. Split unrelated behavior.
- Review the full PR diff against the target branch, not only individual commits.
- Resolve every required check and substantive comment. Record why a suggestion is declined.
- Update the description if scope changes.
- Do not label self-review as independent approval.
- Re-request approval after material changes when repository policy requires it.
- Use the repository's chosen merge policy. Preserve milestone commits when useful; otherwise squash only with owner approval and a clean final message.
- Delete merged branches only under the repository's established policy.
- Release tags and deployment are separate actions requiring explicit approval.

## Handling review fixes

Before review, amend or fix up only with owner approval because it changes commit history. During active review, prefer focused follow-up commits when they make reviewer feedback traceable. Before merge, the owner may approve an interactive rebase/squash. Never force-push without explicit approval; use `--force-with-lease` only when approved and after confirming the remote branch state.

If a commit fails checks, do not conceal or bypass the failure. Fix it within the same branch, rerun validation, present the updated diff, and obtain approval for the corrective commit or amended commit.

## Repository status and evidence

Update `docs/IMPLEMENTATION_STATUS.md` as part of each task with the step, state, behavior delivered, validation, limitations, and next dependency. Do not add the current commit's SHA inside that same commit. Record it after commit in the PR/issue, or in the next approved status update.

Benchmark and evaluation claims must point to versioned run manifests. Do not put aspirational numbers into commit messages, PR titles, résumé bullets, or release notes. Mark draft, fixture-only, unreviewed, and synthetic results clearly.

## Processing the existing `Plans` folder

The six existing handoffs and this workflow form one roadmap documentation set. Since `Plans/` is currently untracked, onboard it as one atomic documentation change before implementation work.

1. On the integration branch, inspect `git status`, tracked files, ignore rules, and remotes without changing history.
2. Ask the owner to approve branch `docs/project-roadmap` and proposed commit `docs: add RetrieVec implementation roadmap`.
3. After approval, create the branch from the current integration branch. Do not edit implementation code on this branch.
4. Ensure `Plans/` contains:
   - `ENGINEERING_WORKFLOW.md`
   - `retrievec_1-2.md`
   - `retrievec_3-4.md`
   - `retrievec_5-6.md`
   - `retrievec_7-8.md`
   - `retrievec_9-10.md`
   - `retrievec_11-12.md`
5. Normalize Markdown formatting and line endings according to `.editorconfig`/`.gitattributes`; do not rewrite technical meaning during normalization.
6. Check internal paths, milestone order, step counts, terminology, and that every handoff references this workflow.
7. Scan for credentials, private document contents, personal contact information, unsupported claims, temporary files, and local-only paths that should not be published.
8. Stage only the seven approved plan files using explicit paths. Review the complete staged diff, whitespace check, and staged file list.
9. Present the staged summary and exact commit message. Commit only after explicit owner approval.
10. After separate approval, push the documentation branch and open a docs-only pull request. Merge through the normal protected-branch process after checks and approval.

Do not split the initial roadmap into one commit per Markdown file; the files constitute one coherent documentation baseline. After onboarding:

- Update a plan in the same feature commit only when the implementation reveals a directly related factual correction.
- Use a separate `docs/...` branch for roadmap changes affecting multiple future milestones or policy.
- Never rewrite a completed milestone to make history look cleaner. Add a dated decision/status note describing what changed and why.
- Keep filenames stable so old issues and PRs retain valid links. Rename only through an explicit docs migration.
- Require this workflow near the top of every future handoff.

## Plan file requirements

Future plan filenames follow `retrievec_<start>-<end>.md` for time-boxed milestones or `retrievec_<Topic>.md` for conditional tracks. Use stable title case and ordinary project language. Every plan includes objective, prerequisites, scope/deferred work, contracts, commit-sized steps, acceptance gates, and a neutral implementation-task prompt.
