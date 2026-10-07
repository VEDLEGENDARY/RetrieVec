from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from retrievec.corpus.sections import Section


class Resource(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Error(Resource):
    code: str
    message: str


class CollectionInput(Resource):
    title: str = Field(min_length=1, max_length=120)


class Collection(Resource):
    collection_id: str
    title: str
    visibility: Literal["private", "curated"]
    active_snapshot: str | None
    can_manage: bool


class SearchInput(Resource):
    collection_id: str = Field(min_length=1, max_length=128)
    query: str = Field(min_length=1, max_length=4096)
    mode: Literal["free_text", "structured"] = "free_text"
    retrieval: Literal["sparse", "dense", "hybrid", "compare"] = "compare"
    snapshot_id: str | None = Field(default=None, pattern=r"^rs_[0-9a-f]{64}$")
    top_k: int = Field(default=10, ge=1, le=100)
    candidates: int = Field(default=100, ge=1, le=1000)
    section: Section | None = None
    rerank: bool = False

    @model_validator(mode="after")
    def valid_combination(self):
        if self.mode == "structured" and self.retrieval != "sparse":
            raise ValueError("structured queries require sparse retrieval")
        if self.top_k > self.candidates:
            raise ValueError("top_k exceeds candidate count")
        if self.rerank and (
            self.retrieval != "hybrid"
            or self.mode != "free_text"
            or self.candidates < 50
            or self.top_k > 50
        ):
            raise ValueError(
                "reranking requires hybrid free-text search with at least 50 candidates"
            )
        return self


class Job(Resource):
    job_id: str
    collection_id: str
    state: str
    stage: str
    progress: dict
    error_code: str | None
    output_snapshot: str | None
