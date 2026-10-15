# Paper workspace

The product starts with research papers and the reader's task: collect, search,
inspect, and reuse evidence. Retrieval methods and experiment settings remain
under progressive disclosure. Source and snapshot provenance remain available.

## Visual direction

Cool paper surfaces (`#f4f6fa`, `#ffffff`), dark slate text (`#182431`), and a
restrained teal action color (`#076454`) support long reading sessions. Georgia
gives the welcome and passage illustration a document character; the existing
system UI font handles controls and metadata. The shared token file owns colors,
spacing, six type roles, radii, and light/dark behavior. Evidence surfaces stay
opaque, with visible keyboard focus, reduced motion, and responsive reflow.

The welcome illustration explains the workflow and explicitly labels itself as
an illustration. It does not invent research results. The workspace uses a compact
collection header and clear destinations; an empty collection shows its next steps.
The first actionable destination after creating a collection is Sources.

## New patterns

- **Research guide:** native modal dialog in the sidebar, with a labeled heading,
  close action, Escape support, and focus return. Provides the first-use workflow,
  file limits, privacy, optional generation, and keyboard shortcuts.
- **Question starters:** buttons that populate the passage composer and focus it.
  They never submit automatically or replace an existing result.
- **Paper library:** a Sources section for original uploaded files, searchable by
  filename, paginated in groups of 25, with status, format, size, and original-source
  links for completed uploads. It distinguishes imported curated records from
  uploaded files and never implies a full-paper corpus for the SciFact starter.
- **Upload handoff:** after successful processing, an action opens Ask. Processing
  job details stay available in their existing disclosure.

## Access and data boundaries

`GET /api/v1/collections/{collection_id}/papers` uses the current authenticated
session and existing live collection read policy before querying filenames. A
parameterized substring query treats `%` and `_` literally; a deterministic
created-time/ID ordering supports cursor pagination without counting every file or
discarding earlier pages. The existing collection index scopes reads. Responses expose
only the fields needed for the library, excluding storage keys, owner IDs, and
source hashes. Original links retain the existing snapshot membership, source
integrity, and authorization checks. No migration is needed.

The library polls only while Sources is visible and aborts requests when scope
changes or the component unmounts. Polling stops after an error until Retry is
chosen. It keeps no filename cache in browser storage. Existing draft/session
isolation and per-collection provider consent remain in their original owners.
