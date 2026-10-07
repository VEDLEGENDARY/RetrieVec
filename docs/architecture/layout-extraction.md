# Optional layout extraction

**Status:** Experimental, opt-in. The product's default `pypdf` upload and
`paragraph-v1` snapshots remain unchanged.

The layout adapter targets [Docling 2.129.0](https://pypi.org/project/docling/)
with its [MIT license](https://github.com/docling-project/docling/blob/main/pyproject.toml).
Its [installation guide](https://docling-project.github.io/docling/getting_started/installation/)
lists Windows, macOS and Linux support. Docling's standard PDF pipeline provides
reading-order and layout detection plus optional OCR. The optional extra is
deliberately separate because it brings PyTorch and model weights; it is not
installed in the default application or container.

Install the `layout` and `extraction` extras in an isolated environment, download
the Docling weights ahead of time, and pin the installed
`retrievec-docling-adapter` entry point's absolute path and SHA256 in an
`AdapterConfig` with `name="docling-layout"`,
`revision="2.129.0+adapter-v1"`, `capabilities=["prose"]` and
`parameters={"images_scale":1.5,"offline":true}`. The adapter refuses version
drift and partial conversion. It writes only prose with real page renders and
source-space coordinates through the existing validated evidence protocol. It
refuses rotated or non-unit PDF pages until their coordinate mapping is tested.
Uncertain pages remain review-dependent; tables and equations are not emitted by
this first adapter. No claim of extraction quality follows from infrastructure
tests alone.

Docling weights must be present locally. Extraction sets Hugging Face offline
flags and disables remote services. The outer adapter runner enforces source,
time, page, file and output limits, verifies its executable hash, and publishes
only a complete validated bundle.
