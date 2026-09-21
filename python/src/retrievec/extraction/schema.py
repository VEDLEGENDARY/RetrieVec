"""Typed source objects with explicit geometry, derivation and review provenance."""

import math
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from retrievec.corpus.snapshot import canonical, digest

Hash = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Text = Annotated[str, Field(min_length=1, max_length=65536)]
Box = tuple[float, float, float, float]


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, allow_inf_nan=False)


class PageGeometry(Strict):
    page: int = Field(ge=1, le=10000)
    media_box: Box
    crop_box: Box
    rotation: Literal[0, 90, 180, 270] = 0
    user_unit: float = Field(default=1, gt=0, le=75000)
    origin: Literal["bottom_left"] = "bottom_left"
    units: Literal["pdf_user_space"] = "pdf_user_space"

    @model_validator(mode="after")
    def bounds(self):
        for box in (self.media_box, self.crop_box):
            if not all(math.isfinite(v) for v in box) or box[0] >= box[2] or box[1] >= box[3]:
                raise ValueError("invalid page box")
        m, c = self.media_box, self.crop_box
        if c[0] < m[0] or c[1] < m[1] or c[2] > m[2] or c[3] > m[3]:
            raise ValueError("crop box is outside media box")
        if max(c[2] - c[0], c[3] - c[1]) * self.user_unit > 14400:
            raise ValueError("display page exceeds bounded dimensions")
        return self

    @property
    def display_size(self):
        x0, y0, x1, y1 = self.crop_box
        width, height = (x1 - x0) * self.user_unit, (y1 - y0) * self.user_unit
        return (height, width) if self.rotation in (90, 270) else (width, height)

    @property
    def display_transform(self):
        x0, y0, x1, y1 = self.crop_box
        s = self.user_unit
        return {
            0: (s, 0, 0, -s, -x0 * s, y1 * s),
            90: (0, s, s, 0, -y0 * s, -x0 * s),
            180: (-s, 0, 0, s, x1 * s, -y0 * s),
            270: (0, -s, -s, 0, y1 * s, x1 * s),
        }[self.rotation]

    def display_box(self, box: Box):
        x0, y0, x1, y1 = box
        c = self.crop_box
        if (
            not all(math.isfinite(v) for v in box)
            or x0 >= x1
            or y0 >= y1
            or x0 < c[0]
            or y0 < c[1]
            or x1 > c[2]
            or y1 > c[3]
        ):
            raise ValueError("source region is outside displayed crop")
        a, b, c, d, e, f = self.display_transform
        points = [(a * x + c * y + e, b * x + d * y + f) for x in (x0, x1) for y in (y0, y1)]
        return (
            min(p[0] for p in points),
            min(p[1] for p in points),
            max(p[0] for p in points),
            max(p[1] for p in points),
        )


class Review(Strict):
    status: Literal["pending", "reviewed", "rejected"] = "pending"
    reviewer: str | None = Field(default=None, min_length=1, max_length=128)
    rationale: str | None = Field(default=None, min_length=1, max_length=4096)

    @model_validator(mode="after")
    def provenance(self):
        if self.status == "pending" and self.reviewer is not None:
            raise ValueError("pending evidence cannot claim a reviewer")
        if self.status != "pending" and (not self.reviewer or not self.rationale):
            raise ValueError("review decisions require reviewer and rationale")
        return self


class Prose(Strict):
    kind: Literal["prose"] = "prose"
    text: Text


class Cell(Strict):
    row: int = Field(ge=0, le=255)
    column: int = Field(ge=0, le=255)
    row_span: int = Field(default=1, ge=1, le=256)
    column_span: int = Field(default=1, ge=1, le=256)
    text: str = Field(max_length=4096)
    role: Literal["data", "column_header", "row_header", "corner"] = "data"
    unit: str | None = Field(default=None, max_length=128)
    missing: bool = False
    ambiguous: bool = False
    bbox: Box | None = None


class Table(Strict):
    kind: Literal["table"] = "table"
    rows: int = Field(ge=1, le=256)
    columns: int = Field(ge=1, le=256)
    cells: list[Cell] = Field(max_length=10000)
    caption: str = Field(default="", max_length=4096)
    footnotes: list[Text] = Field(default_factory=list, max_length=64)

    @model_validator(mode="after")
    def grid(self):
        occupied = set()
        for cell in self.cells:
            if (
                cell.row + cell.row_span > self.rows
                or cell.column + cell.column_span > self.columns
            ):
                raise ValueError("cell span is outside table")
            if cell.missing and cell.text.strip():
                raise ValueError("missing cell cannot assert a value")
            for row in range(cell.row, cell.row + cell.row_span):
                for column in range(cell.column, cell.column + cell.column_span):
                    if (row, column) in occupied:
                        raise ValueError("overlapping table cells")
                    occupied.add((row, column))
        return self


class Equation(Strict):
    kind: Literal["equation"] = "equation"
    transcription: Text
    notation: Literal["latex", "plain"] = "plain"
    label: str | None = Field(default=None, max_length=128)
    definitions: list[Text] = Field(default_factory=list, max_length=64)
    equivalence: Literal["unverified"] = "unverified"


class Observation(Strict):
    text: Text
    basis: Literal["visible_label", "qualitative_interpretation"]
    uncertain: bool = True


class Figure(Strict):
    kind: Literal["figure"] = "figure"
    caption: str = Field(default="", max_length=4096)
    observations: list[Observation] = Field(default_factory=list, max_length=64)
    precise_values: Literal["not_established"] = "not_established"


Content = Annotated[Prose | Table | Equation | Figure, Field(discriminator="kind")]


class Evidence(Strict):
    schema_version: Literal[1] = 1
    source_sha256: Hash
    geometry: PageGeometry
    bbox: Box
    page_render_sha256: Hash
    region_crop_sha256: Hash | None = None
    extractor: str = Field(min_length=1, max_length=128)
    revision: str = Field(min_length=1, max_length=256)
    configuration: dict = Field(default_factory=dict)
    raw_output: Text
    content: Content
    derivation: Literal["text_layer", "ocr", "model_derived", "manual"]
    confidence: float | None = Field(default=None, ge=0, le=1)
    warnings: list[Text] = Field(default_factory=list, max_length=64)
    review: Review = Field(default_factory=Review)

    @model_validator(mode="after")
    def region(self):
        self.geometry.display_box(self.bbox)
        if len(canonical(self.configuration)) > 16384:
            raise ValueError("extractor configuration exceeds limit")
        if self.content.kind in ("equation", "figure") and self.region_crop_sha256 is None:
            raise ValueError("visual evidence requires a retained crop")
        if isinstance(self.content, Table):
            for cell in self.content.cells:
                if cell.bbox is not None:
                    self.geometry.display_box(cell.bbox)
                    if (
                        cell.bbox[0] < self.bbox[0]
                        or cell.bbox[1] < self.bbox[1]
                        or cell.bbox[2] > self.bbox[2]
                        or cell.bbox[3] > self.bbox[3]
                    ):
                        raise ValueError("cell region is outside table region")
        return self

    @property
    def identity(self):
        return "eo_" + digest(canonical(self.model_dump(mode="json")))

    @property
    def synthesis_allowed(self):
        if self.review.status == "rejected":
            return False
        if self.derivation != "text_layer" and self.review.status != "reviewed":
            return False
        if self.content.kind != "prose" and self.review.status != "reviewed":
            return False
        if isinstance(self.content, Table) and any(cell.ambiguous for cell in self.content.cells):
            return False
        return not self.warnings and (self.confidence is None or self.confidence >= 0.9)

    def locator(self):
        return {
            "page": self.geometry.page,
            "bbox": list(self.bbox),
            "geometry": self.geometry.model_dump(mode="json"),
            "display_box": list(self.geometry.display_box(self.bbox)),
            "display_size": list(self.geometry.display_size),
            "display_transform": list(self.geometry.display_transform),
        }
