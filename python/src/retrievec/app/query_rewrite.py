"""Bounded, deterministic follow-up context; never introduces generated facts."""


def rewrite_query(question: str, parent: dict | None) -> str:
    question = question.strip()
    if not question:
        raise ValueError("Enter a question")
    if parent is None or question == parent["original_question"].strip():
        return question
    # Original questions avoid recursively growing earlier rewritten queries.
    context = parent["original_question"].strip()
    rewritten = f"Previous question: {context}\nFollow-up question: {question}"
    if len(rewritten) > 4096:
        raise ValueError("Follow-up context exceeds the query budget; enter a standalone query")
    return rewritten
