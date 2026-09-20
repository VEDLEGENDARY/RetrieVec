"""Strict structural checks; semantic claim support still requires human review."""

import re
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

Text = Annotated[str, StringConstraints(min_length=1, max_length=4096)]
Identity = Annotated[str, StringConstraints(pattern=r"^[a-zA-Z0-9_-]{1,80}$")]
MISSING = "not reported in retrieved evidence"


class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Quote(Strict):
    evidence_id: Identity
    text: Text


class Claim(Strict):
    id: Identity
    text: Text
    evidence_ids: list[Identity] = Field(min_length=1, max_length=8)
    support_status: Literal["structurally_valid"]
    quotes: list[Quote] = Field(min_length=1, max_length=8)


class Comparison(Strict):
    method: Text
    dataset: Text
    metric: Text
    reported_value: Text
    experimental_conditions: Text
    limitations: Text
    evidence_ids: list[Identity] = Field(min_length=1, max_length=8)
    comparability_note: Text


class Answer(Strict):
    status: Literal["answered", "insufficient_evidence", "partial"]
    claims: list[Claim] = Field(max_length=12)
    comparisons: list[Comparison] = Field(max_length=12)
    limitations: list[Text] = Field(max_length=12)


def abstention(reason="No relevant evidence was retrieved"):
    return {
        "status": "insufficient_evidence",
        "claims": [],
        "comparisons": [],
        "limitations": [reason],
    }


def validate_answer(raw: str, evidence: list[dict]) -> dict:
    if len(raw.encode("utf-8")) > 65536:
        raise ValueError("answer too large")
    answer = Answer.model_validate_json(raw)
    sources = {item["evidence_id"]: item for item in evidence}
    if len(sources) != len(evidence):
        raise ValueError("duplicate evidence identity")
    if not evidence and answer.model_dump() != abstention():
        if answer.status != "insufficient_evidence" or answer.claims or answer.comparisons:
            raise ValueError("answer without evidence")
    if answer.status == "insufficient_evidence" and (answer.claims or answer.comparisons):
        raise ValueError("abstention cannot contain supported claims")
    if answer.status in ("answered", "partial") and not answer.claims:
        raise ValueError("answer must contain claims")
    if len({claim.id for claim in answer.claims}) != len(answer.claims):
        raise ValueError("duplicate claim identity")
    for item in [*answer.claims, *answer.comparisons]:
        if len(set(item.evidence_ids)) != len(item.evidence_ids):
            raise ValueError("duplicate citation")
        if any(identity not in sources for identity in item.evidence_ids):
            raise ValueError("unknown evidence identity")
        supplied = " ".join(sources[identity]["text"] for identity in item.evidence_ids)
        text = item.text if isinstance(item, Claim) else item.reported_value
        # Reject invented numerical literals; matching numbers are not semantic proof.
        if set(re.findall(r"\d+(?:\.\d+)?", text)) - set(re.findall(r"\d+(?:\.\d+)?", supplied)):
            raise ValueError("unsupported numerical literal")
    for claim in answer.claims:
        if set(claim.evidence_ids) != {quote.evidence_id for quote in claim.quotes}:
            raise ValueError("each cited passage needs an exact quote")
        for quote in claim.quotes:
            if quote.text not in sources[quote.evidence_id]["text"]:
                raise ValueError("quote is absent from evidence")

    result = answer.model_dump()

    def safe(value):
        if isinstance(value, str) and re.search(
            r"<[^>]*>|(?:https?|javascript|data):", value, re.I
        ):
            raise ValueError("answer contains markup or an untrusted link")
        if isinstance(value, dict):
            for item in value.values():
                safe(item)
        elif isinstance(value, list):
            for item in value:
                safe(item)

    safe(result)
    return result
