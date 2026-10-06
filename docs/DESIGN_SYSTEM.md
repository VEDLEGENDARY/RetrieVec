# Workspace design system

The workspace uses `web/src/tokens.css` for presentation decisions and `web/src/ui.tsx` for shared controls. Search ranking, source geometry, upload retry keys, research transitions, authorization, consent, and snapshot semantics remain in their domain modules.

The [material contract](design/MATERIALS.md) documents the 2026-10-06 refinement:
optional glass chrome, solid reading surfaces, sampled spring easing and explicit
reduced-transparency/forced-color fallbacks. `WorkspaceChrome.tsx` owns presentation
for the collection header and three destinations; domain state remains in the app.

## Tokens

| Category | Contract |
| --- | --- |
| Color | Semantic canvas, surface, ink, muted, border, brand, danger, action, disabled, overlay, and highlight roles. System dark mode overrides the relevant roles. Action backgrounds keep readable white text in both themes. |
| Type | Six sizes: metadata, supporting, body, subheading, section heading, page heading. System UI fonts for controls, Georgia with serif fallbacks for evidence, system monospace for code. No Inter download or assumption. |
| Space | Multiples of 4px at the default 16px root size. Responsive padding compositions refer to those tokens. |
| Radius | Control, card, overlay, pill, circle. |
| Elevation | Small surface, raised surface, overlay, and focus ring. |
| Motion | 150/200/250ms; reduced-motion override is 0.01ms. Named easing and explicit transitioned properties. |

Layout constraints (viewport proportions, content widths, grid columns), CSS breakpoints, zero values, and SVG source/artwork geometry are not spacing tokens. File-size limits, timers for network retries, and evidence coordinates are behavioral data and are unchanged.

Native controls inherit `color-scheme`. `web/scripts/sync-brand.mjs` generates the favicon palette and light/dark `theme-color` metadata from the token source. Run `node scripts/sync-brand.mjs` from `web` after changing the palette; `npm run build` rejects stale generated assets. Static SVG drawing geometry remains artwork. Evidence highlights use a semantic stroke and white halo against retained source images, whose colors do not follow the app theme; this does not introduce exact highlights for ordinary PDFs.

## Shared components

| Component | Use and accessibility contract |
| --- | --- |
| `Button` | Primary, secondary/base, quiet; native type, events and ARIA pass through. `loading` sets disabled and `aria-busy`. Callers retain truthful visible progress text and existing submission guards. |
| `ActionLink` | Navigation actions remain anchors with original destinations, target and rel attributes. |
| `IconButton` | Requires an accessible name; consistent control size. Decorative Lucide icons are hidden from the accessibility tree. |
| `Field` + `Input` / `Select` / `Textarea` | One label and control; preserves explicit IDs/refs and existing descriptions. Optional description/error IDs are combined in `aria-describedby`; errors set `aria-invalid` and announce through an alert. Native required/limits remain unchanged. |
| `Surface` | Shared border, background, radius and elevation; solid by default. Optional glass adds a bounded pointer-responsive rim with accessibility-preference guards. Domain classes retain layout differences. |
| `Notice` | Persistent error alert or polite informational status; supports an optional action. Routine field help and progress text are not automatically alerts. |
| `EmptyState` / `LoadingState` | Composable empty-state action; one announced loading label and decorative skeleton bars. No invented percentages. |
| `StatusBadge` | Info/success/error presentation. `presentation.ts` maps API states to public labels without altering enum values. Unknown states display “Status unavailable”. |
| `Disclosure` / `More` | Native details/summary semantics and caller-controlled open state; `More` adds a labeled content area. |
| `NativeDialog` | Shared presentation and native modal element. Command menu and navigation retain their existing focus, Escape, backdrop and lifecycle logic. Evidence inspectors remain nonmodal. |

All authored native button, form-control, label, details, and dialog elements now live in `ui.tsx`. The original audit's 32 buttons describe its historical baseline, not the current number of controls. `scripts/check_design_tokens.py` prevents raw control sites outside the shared module, design literals in guarded declarations, and additional type-size roles.

## Vocabulary and errors

Workspace → Collection → Source → Passage / Evidence. Answer composition is **Cited answers**; history is **Saved research**. Keep **Snapshot**, **Open original source**, and **Sign in / Sign out** consistent. Selection/upload still uses “file” and “document” where those are accurate.

Errors describe what happened and an available next action. Server guidance and access/uncertain-upload distinctions are preserved. Unknown network failures receive recoverable copy; error codes are unchanged. OCR copy describes the default readable-text upload path and points to operator-configured advanced extraction without promising it is enabled.

## Reproduce the UI evidence

```sh
python scripts/check.py
cd web
npm run build
npm run test:ui -- --workers=2
```

`ui-tests/design-system.spec.ts` captures the current screen inventory at 1280px and 390px, light and dark. Each PNG is attached to the Playwright test and saved under `web/test-results/design-system-screen-inventory-<width>-<theme>/`. `screen-and-contrast-report.json` records the captured names, computed foreground/background values, and measured ratios. These generated artifacts remain ignored; tests and verification summaries are committed. These are captures with behavioral/axe assertions, not approved golden-image comparisons.

The matrix covers opening, signed-out and empty workspaces; collection readiness and details; search/results/no matches/recent searches; shortlist; ordinary and structured evidence inspection (table/equation/figure/prose/error); upload validation and processing states; cited answers/provider consent; saved research and run states; citation inspection; quick actions/no matches; mobile navigation; archive Undo. Overview and browser archive confirmation are no longer standalone screens on the `main` baseline; their current equivalents are captured. External identity-provider pages remain outside this application's UI inventory.

Automated checks include WCAG-tagged axe rules, rendered text/focus contrast, disabled hover, field associations, theme metadata, horizontal overflow, reduced motion, forced-colors focus, and a supplemental 640px reflow capture. Existing tests retain keyboard shortcuts, Escape/focus return, session cleanup, streaming revocation, drafts, and upload retry behavior. This is Chromium fixture coverage, not a manual screen-reader certification or real-service integration test. Browser zoom, other browser engines, and external authentication require separate manual/integration review.
