# Reading Room foundation verification — 2026-10-14

Task 1 establishes the visual direction documented in
[Reading Room with an Atlas](../design/READING_ROOM.md). The Evidence Atlas's
actual projection and interaction implementation remains part of Page 3.

| Check | Result |
|---|---|
| Production frontend | TypeScript and Vite build pass. All font assets and OFL notices are bundled locally. |
| Contrast script | 88 allowed text/surface pairs pass in light and dark. Minimum: 4.570:1, light Flag Coral on the derived plum surface. Named fluid steps and shared-token rules pass. |
| Browser suite | 45 tests pass, including four desktop/mobile light/dark inventories with rendered contrast measurements and axe scans. |
| Final focused checks | Four reading-room checks pass after final result-motion cleanup, and the final saved-research check passes with explicit citation hover/focus highlighting and Escape dismissal. |
| Appearance | System preference, manual override, reload persistence, live OS changes, cross-tab synchronization, and blocked-storage fallback are exercised. |
| Typography and privacy | Browser checks confirm locally loaded Newsreader, Geist, and Geist Mono; 18px / 29.7px reading text; metric tabular numerals; Geist shortcuts; method mark colors; and zero third-party requests in the tested UI flow. |
| Motion and reflow | Reduced motion prevents result movement; existing reduced-motion checks, 320px doubled-text reflow, keyboard focus, and forced-color checks pass. Result positions use document coordinates so page scrolling is excluded from method-change motion. |
| Static checks | Ruff lint/format for the modified contrast checker, brand-generation check, and Git whitespace check pass. |

The font installation reports zero npm vulnerabilities. The existing Lucide
module-level `use client` notices remain build warnings.

Browser HTTP fixtures are synthetic; these checks make no retrieval, generation,
embedding, citation-semantic, or scientific-quality claims. No backend contract,
source integrity, authorization, or database schema change is introduced.
Manual screen-reader review and browser engines other than Chromium were not run.
