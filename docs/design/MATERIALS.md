# Research workspace materials

> Historical direction, superseded by [Reading Room with an Atlas](READING_ROOM.md).
> The current interface uses opaque surfaces, self-hosted Newsreader and Geist,
> and the teal/plum retrieval palette. Reflective materials are retired.

The visual brief draws on Apple desktop and mobile conventions: quiet chrome,
tactile controls, clear depth and adaptable text. This is a design direction,
not an Apple endorsement, award claim or accessibility certification.

## Decisions

| Layer | Treatment | Purpose |
|---|---|---|
| Canvas | Cool mist `#f2f5f9`; dark slate `#111923` | Separate the workspace from its reading surfaces. |
| Reading | Solid white / `#1b2734` | Keep passages, forms and citations legible independently of backdrop content. |
| Chrome | Nearly opaque material tint, 20px backdrop blur and a masked light rim | Establish hierarchy without putting text over moving imagery. |
| Actions | Existing teal semantic roles | Preserve identity and keep emphasis on the next research action. |
| Elevation | Theme-specific surface, raised and overlay shadows | Distinguish cards, selected navigation and dialogs. |

The six type roles and 4px spacing scale remain intact. The system font stack
prefers Apple system fonts when available, then Segoe UI Variable/Segoe UI and
other system fallbacks. Optical sizing is enabled where the chosen font supports
it. No proprietary or remote font is assumed or downloaded. Evidence retains its
serif reading face and provenance remains in the code face.

`CollectionHeader` and `WorkspaceDestinations` are presentation modules. The app
retains collection selection, route state, archive actions and provider consent.
`Surface` accepts an optional glass material; solid is its default. Its masked
rim responds to mouse position using bounded element-local CSS properties. It
does not update React state, retain pointer data or run a perpetual animation.
The highlight approximates a changing material reflection; it is not physical
ray-traced refraction or a spatial-computing renderer.

Controls use a sampled unit-mass damped spring (damping ratio 0.8, natural angular
frequency 32/s, 33 samples over 250ms) in CSS `linear()`, with a cubic fallback.
The 150–250ms motion contract is preserved. Disabled controls never get the press
transform. Native activation, focus outlines and keyboard behavior are retained.

## Inclusive fallbacks

- Reduced motion suppresses pointer response and reduces transition durations.
- Reduced transparency removes blur and the reflective rim, using solid chrome.
- Forced colors removes decorative material effects while retaining native
  semantic surfaces and focus outlines.
- All three destination controls fit a single navigation group on narrow screens.
  Layout supports 320px with doubled root text; this is a reflow test, not a claim
  of manual browser-zoom or screen-reader certification.
- Unfocused and hovered input borders meet 3:1 on their rendered reading surface.
  The selected destination has an explicit contrasting border and stronger text
  weight; its selected state does not depend on a faint surface tint.
- Source images keep their original colors. Exact PDF highlights still require
  verified retained locators; unavailable coordinates are never guessed.

The 2026-10-06 run passed 33 Chromium UI tests and produced 144 inventoried
screen captures at 1280px/390px in both themes. New checks cover pointer response,
solid text plates, reduced-transparency/forced-color fallbacks and all three
destinations at 320px with doubled text. Existing checks retain axe, rendered
text/focus contrast, shortcuts, Escape/focus return, consent, upload retry keys,
session cleanup and provenance. Human visual approval, manual assistive-technology
review and other browser engines remain open gates.

See [repository closure](../maintenance-2026-10-06.md) for issue dispositions,
commands, results and review limits.
