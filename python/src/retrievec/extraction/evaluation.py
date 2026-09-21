"""Bounded extraction measurements; semantic and mathematical reviews remain explicit."""

import re


def distance(reference, observed):
    if len(reference) * len(observed) > 4_000_000:
        raise ValueError("edit-distance comparison exceeds computation budget")
    if len(reference) < len(observed):
        reference, observed = observed, reference
    previous = list(range(len(observed) + 1))
    for i, left in enumerate(reference, 1):
        current = [i]
        for j, right in enumerate(observed, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (left != right)))
        previous = current
    return previous[-1]


def prose_metrics(reference, observed):
    characters = distance(reference, observed)
    words = reference.split()
    word_errors = distance(words, observed.split())
    return {
        "character_edits": characters,
        "reference_characters": len(reference),
        "character_error_rate": characters / len(reference) if reference else None,
        "word_edits": word_errors,
        "reference_words": len(words),
        "word_error_rate": word_errors / len(words) if words else None,
        "reading_order_review": "pending",
    }


def table_metrics(reference, observed):
    expected = {(cell.row, cell.column): cell for cell in reference.cells}
    actual = {(cell.row, cell.column): cell for cell in observed.cells}
    aligned = set(expected) & set(actual)
    spans = sum(
        (expected[key].row_span, expected[key].column_span)
        == (actual[key].row_span, actual[key].column_span)
        for key in aligned
    )
    headers = [key for key, cell in expected.items() if cell.role != "data"]
    numbers = [key for key, cell in expected.items() if re.search(r"\d", cell.text)]
    return {
        "reference_cells": len(expected),
        "aligned_cells": len(aligned),
        "missing_cells": len(set(expected) - set(actual)),
        "extra_cells": len(set(actual) - set(expected)),
        "matching_spans": spans,
        "reference_headers": len(headers),
        "matching_headers": sum(
            key in actual
            and expected[key].text == actual[key].text
            and expected[key].role == actual[key].role
            for key in headers
        ),
        "reference_numeric_cells": len(numbers),
        "exact_numeric_and_unit_matches": sum(
            key in actual
            and expected[key].text == actual[key].text
            and expected[key].unit == actual[key].unit
            and not actual[key].ambiguous
            for key in numbers
        ),
        "semantic_table_review": "pending",
    }


def locator_iou(reference, observed):
    if any(box[0] >= box[2] or box[1] >= box[3] for box in (reference, observed)):
        raise ValueError("invalid locator box")
    intersection = max(0, min(reference[2], observed[2]) - max(reference[0], observed[0])) * max(
        0, min(reference[3], observed[3]) - max(reference[1], observed[1])
    )
    areas = sum((box[2] - box[0]) * (box[3] - box[1]) for box in (reference, observed))
    return intersection / (areas - intersection)
