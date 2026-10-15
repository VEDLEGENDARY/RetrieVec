# Search and evidence workbench

Task 02 builds on the merged Reading Room foundation. All changes are confined to `web/`.

`src/features/search/SearchPage.tsx` composes the query, result list, comparison drawer, recent searches, source inspector, and reserved Atlas panel. `useEvidenceWorkbench` owns requests through the existing API client, cancellation, caching, filters, recent searches, shortlist, clipboard, and JSON downloads. Components do not issue search requests.

## Evidence identity and method switching

Every request includes its intended snapshot. Responses with a different snapshot or collection are rejected without replacing retained evidence. Cache keys include query, snapshot, syntax, section, and reranking configuration. Each key retains the returned method rankings; switching to a cached method does not issue another request. Missing rankings are requested for the same snapshot. A method change during a pending query cancels that request and restarts the pending question with the new method.

Cards remain keyed by snapshot and passage ID. A FLIP animation uses the actual before/after positions for approximately 250 ms when methods reorder cards. Reduced motion skips the animation, including when the preference changes during it. Explicit method filters display that method's marks, ranks, scores, and order. Method scores keep their own labels and scales.

Recent searches retain the last five successful query configurations. Choosing one restores fields without executing a request. Shortlists retain up to six passages with their original question, snapshot, exact content, returned methods, and per-method ranks and scores. These states live only in the mounted principal/collection workbench, survive navigation within the collection, and clear on collection change or reload. Query drafts retain the application's existing device-storage behavior.

## Reading and accessibility

Passages use the local Newsreader font at 18 px / 1.65 and a maximum 65-character measure. Cards reserve the same height as their loading skeletons; long text scrolls in a labelled, keyboard-focusable reading region. Sparse and hybrid highlights are plain React text nodes and `mark` elements. Passage HTML is never interpreted.

The method switch uses native radios. Recent searches support Arrow keys, Home, End, Enter, and Escape. The native comparison dialog contains focus, restores its trigger on close, and supports horizontal scroll snap on mobile. Source links retain snapshot identities. Source SHA-256 prefixes appear only when returned as actual hashes; the current API may omit them, in which case the interface explicitly says unavailable. IDs are never substituted for hashes.

Empty collections, initial search, loading, empty results, filtered empty results, network errors, missing comparison methods, and failed method changes each have an explanation and next action. Available evidence survives partial failures. Authentication failures clear private cached evidence through the existing session failure flow.

`AtlasPanel` deliberately renders “Atlas arrives in task 04”. Its `selectedPassageId` and `highlights` props carry actual passage IDs, methods, and ranks for the later visualization.

## Verification

Run from `web/`:

```sh
npm run build
npm run test:unit
npm run test:ui
npm run test:lighthouse
```

`test:ui` also runs the pure-helper unit tests. Playwright covers caching and reordering, pending-request method changes, snapshot pinning, partial failures, method filtering, the shortlist limit, comparison, export shape, recent-search keyboard controls, source actions, focus containment, mobile reflow, safe text rendering, and matching loading geometry. Axe runs against the loading and loaded search page in both themes at desktop and mobile widths, and against the mobile comparison drawer. The layout-shift observer records loading shifts independently of recent-input exclusions by also comparing exact skeleton/card positions and heights.

`test:lighthouse` serves the production build with synthetic local evidence and saves the light/dark Lighthouse accessibility reports under ignored `test-results/lighthouse-search/`. No external retrieval, generation, or research-quality claim is made by these fixtures. Real service integration remains covered by `tests/workspace.spec.ts` and its isolated PostgreSQL environment in CI.
