"""Automatic answer diagnostics. These signals are not human relevance judgments."""

from __future__ import annotations

import re
from collections.abc import Callable

from retrievec.app.answers import validate_answer

NUMBER = re.compile(r"(?<!\w)\d+(?:[.,]\d+)*(?:%|\b)")
WORD = re.compile(r"[\w]+", re.UNICODE)


def _tokens(value: str) -> set[str]:
    return {token.casefold() for token in WORD.findall(value) if len(token) > 2}


def _claims(answer: dict) -> list[dict]:
    return [*answer.get("claims", []), *answer.get("comparisons", [])]


def automatic_signals(
    raw: str,
    evidence: list[dict],
    *,
    expected_unanswerable: bool | None = None,
    entailment: Callable[[str, str], float] | None = None,
) -> dict:
    """Score a provider output without implying semantic truth.

    The optional entailment callable receives (premise, hypothesis). Its model
    identity and calibration must be recorded by the caller before interpreting
    scores. A lexical overlap fallback is deliberately named as such.
    """
    result = {
        "structurally_valid": False,
        "citation_precision": None,
        "quote_coverage": None,
        "unsupported_numeral_rate": None,
        "abstention_correct": None,
        "entailment_proxy": None,
        "entailment_proxy_kind": "model_nli" if entailment else "lexical_overlap_not_nli",
        "failure": None,
    }
    try:
        answer = validate_answer(raw, evidence)
    except (ValueError, TypeError) as error:
        result["failure"] = type(error).__name__ + ": " + str(error)[:240]
        return result
    result["structurally_valid"] = True
    if expected_unanswerable is not None:
        result["abstention_correct"] = (
            answer["status"] == "insufficient_evidence"
        ) == expected_unanswerable
    sources = {item["evidence_id"]: item["text"] for item in evidence}
    items = _claims(answer)
    citations = [identity for item in items for identity in item["evidence_ids"]]
    result["citation_precision"] = (
        sum(identity in sources for identity in citations) / len(citations) if citations else None
    )
    quotes = [quote for claim in answer["claims"] for quote in claim["quotes"]]
    result["quote_coverage"] = (
        sum(quote["text"] in sources[quote["evidence_id"]] for quote in quotes) / len(quotes)
        if quotes
        else None
    )
    numerals, unsupported, proxies = 0, 0, []
    for item in items:
        claim = item["text"] if "text" in item else item["reported_value"]
        premise = " ".join(sources[identity] for identity in item["evidence_ids"])
        claimed_numbers = NUMBER.findall(claim)
        numerals += len(claimed_numbers)
        supported_numbers = set(NUMBER.findall(premise))
        unsupported += sum(number not in supported_numbers for number in claimed_numbers)
        if entailment:
            score = float(entailment(premise, claim))
            if not 0 <= score <= 1:
                raise ValueError("NLI score must be in [0, 1]")
        else:
            terms = _tokens(claim)
            score = len(terms & _tokens(premise)) / len(terms) if terms else 0.0
        proxies.append(score)
    result["unsupported_numeral_rate"] = unsupported / numerals if numerals else None
    result["entailment_proxy"] = sum(proxies) / len(proxies) if proxies else None
    return result
