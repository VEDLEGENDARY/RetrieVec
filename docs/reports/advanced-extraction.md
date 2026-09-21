# Weeks 9–10 capability record

Instructions: owner-pasted Weeks 9–10 entry. Work is uncommitted. No real OCR/model
comparison, hardware smoke, reviewed document benchmark or human acceptance has run.

| Capability | Current implementation status |
|---|---|
| Existing text ingestion | Preserved; no new mandatory heavy dependency |
| Page classification | Implemented heuristic routing; error rates unmeasured |
| Coordinates | Crop, rotation, user-unit transforms and bounds implemented; tests authored |
| OCR execution | Experimental pinned local adapter protocol connected to bounded ingestion subprocesses; no OCR executable/model selected |
| Reading order | Experimental region-based XY-cut; one prose layer per page |
| Tables | Structured cells/headers/spans/units/ambiguity and searchable representation implemented; automatic detector not supplied |
| Equations | Crop/transcription/definition/review model implemented; automatic transcription and equivalence unsupported |
| Figures | Crop/caption/qualified observation model implemented; precise numeric inference unsupported |
| Typed indexing | Retained bundle-to-chunk mapping with new snapshot identity; controlled registry-worker configuration |
| Inspection | Authorized pinned-object/page/original routes and structured browser inspector implemented |
| Synthesis | Unreviewed or low-quality derived objects excluded; numeric support excludes generated table coordinates |
| Evaluation | Bounded prose/table/locator metrics and synthetic regression cases; real reviewed dataset pending |
| Remote extraction | Unsupported; no cloud transport or consent workflow enabled |

Six synthetic coordinate/artifact/representation tests passed; Python lint and frontend
TypeScript compilation passed. These checks do not establish OCR accuracy or browser
overlay correctness. `scripts/review_evidence.py` accepts explicit human decisions and
publishes a new bundle with retained review lineage; no review decisions were submitted
in this implementation batch.

Evidence remains source-bound and immutable. Original PDFs and validated PNG renders
are retained. Adapter-generated data cannot mark itself human-reviewed. Raw objects
survive text flattening. Core chunk and Go segment formats are unchanged.

Page routing uses the existing pinned pypdf dependency. Its [official extraction
documentation](https://pypdf.readthedocs.io/en/6.18.1/user/extract-text.html) separates
text extraction from OCR and cautions about positional complexity. The implementation
does not turn text offsets into visual bounding boxes. OCR/model license selection,
resource rehearsal, locator inspection and measured quality remain release gates.
