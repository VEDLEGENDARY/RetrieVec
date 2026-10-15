# Reading Room with an Atlas

RetrieVec turns local papers into searchable, citable evidence. Its interface
should make the chain of trust easy to follow: answer → retained passage →
source hash and immutable snapshot. Reading comes first. The Evidence Atlas is
the one deliberate visual centerpiece; surrounding controls stay quiet.

## Task 1 foundation

The existing reading and research workflows retain their API contracts and
authorization. Navigation, forms, and paper libraries use opaque surfaces,
generous margins, restrained borders, and left-aligned copy. The previous
reflective header, pointer-tracking rim, and spring overshoot are retired.

| Role | Light | Dark |
|---|---|---|
| Vellum / Deep Basin | `#E9EDE8` | `#0D1A1C` |
| Ink Moss / Mist | `#1B2926` | `#E4ECE8` |
| Lens Teal: sparse retrieval, primary actions | `#0B6B6A` | `#46C2BF` |
| Citation Plum: dense retrieval, citations | `#7A3E9D` | `#C79BEA` |
| Flag Coral: errors, partial or insufficient answers | `#B93A20` | `#FF8A6B` |

`web/src/tokens.css` is the source of truth. Derived opaque surfaces and muted
text also live there. Hybrid result headings and each result use a hard split
teal/plum mark. Labels accompany all method marks so meaning survives color
vision differences. Selected results retain a visible border. Scores describe
ranking; partial-answer styling does not imply calibrated model confidence.

Appearance offers System, Light, and Dark on the welcome page and in workspace
navigation. System follows live OS preference changes. A same-origin script
restores manual preference before first paint without weakening the existing
Content Security Policy. Manual changes synchronize between tabs; blocked
storage still permits changes for the current tab. Browser chrome follows the
resolved appearance.

## Typography

Newsreader Variable serves headings and reading text. Answers, excerpts,
passages, citation previews, and drafts use 18px at 1.65 line height, capped at
65ch. Narrow containers use their available width. Geist Variable serves the
interface, including keyboard shortcuts. Geist Mono Variable is reserved for
actual IDs, hashes, metrics, and diagnostic data. Tables and metrics use tabular
numerals. Headings balance and prose wraps with `pretty`.

Full passages use a single reading column. Compact results may place methods
side by side with two-line excerpts; readers can restore the full reading view.

The fluid scale is `--t-0` through `--t-6`. Existing `--type-*` names alias those
steps for migration; reading size remains a dedicated 1.125rem role. All three
families ship in `@fontsource-variable/*` packages with their licenses. Newsreader
includes weight and optical-size axes plus italic. Vite bundles WOFF2 files
locally; no font CDN, analytics, or other third-party runtime resource is added.
The production bundle also includes each font's OFL notice in `/font-licenses/`.

## Motion

- The Atlas's future first-load sequence gets the single orchestrated moment:
  points settle from noise to real embedding clusters in about 1.6 seconds
  (`--motion-atlas-settle`). Its implementation belongs to the Page 3 task.
  No generated point cloud or simulated evidence map is included in Task 1.
- Changing the displayed retrieval method moves shared returned passages into
  their new positions over 200ms. Their order comes from the returned ranks.
- Hovering or focusing a citation reveals its plum passage preview and
  highlights the matching passage if its inspector is open. Escape dismisses
  the preview. Opening an inspector or mobile navigation moves that panel
  along its opening direction.
- Other transitions answer user actions. There are no scroll-triggered reveals,
  ambient animations, or decorative load sequences.
- Reduced motion disables result movement and reduces CSS animations and
  transitions to effectively instantaneous responses.

## Verification

`scripts/check_design_tokens.py` enforces shared tokens and the seven named
steps, and computes WCAG relative luminance from the actual CSS values. It
resolves aliases and light/dark values and checks every allowed text role on
every opaque reading surface, plus primary action states: 88 pairs at 4.5:1
minimum. It fails on unsupported color syntax rather than guessing.

`web/ui-tests/design-system.spec.ts` additionally measures rendered contrast
and scans the screen inventory in both themes on desktop and mobile.
`reading-room.spec.ts` exercises theme persistence, cross-tab changes, blocked
storage, loaded fonts, third-party requests, method semantics, typography, and
reduced motion. Fixtures are synthetic and make no research-quality claims.

The Evidence Atlas still needs Page 3's interaction and data specification,
including actual projection coordinates and a clear account of what distances
mean. Task 1 establishes its palette, typography, and motion contract.
