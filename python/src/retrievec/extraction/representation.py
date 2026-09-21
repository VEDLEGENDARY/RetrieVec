"""Readable search text that retains structure and never manufactures missing values."""

from retrievec.extraction.schema import Equation, Evidence, Figure, Prose, Table

REPRESENTATION_VERSION = "typed-evidence-text-v1"


def numeric_text(evidence):
    content = evidence.content
    if isinstance(content, Table):
        return "\n".join(
            [
                content.caption,
                *content.footnotes,
                *[
                    cell.text + " " + (cell.unit or "")
                    for cell in content.cells
                    if not cell.missing
                ],
            ]
        )
    if isinstance(content, Prose):
        return content.text
    if isinstance(content, Equation):
        return "\n".join([content.transcription, *content.definitions])
    return ""


def searchable(evidence: Evidence):
    content = evidence.content
    prefix = f"[{content.kind}; {evidence.derivation}; review={evidence.review.status}]"
    if isinstance(content, Prose):
        body = content.text
    elif isinstance(content, Equation):
        body = "\n".join(
            [
                f"Equation {content.label or '(unlabeled)'}: {content.transcription}",
                "Mathematical equivalence unverified.",
                *content.definitions,
            ]
        )
    elif isinstance(content, Figure):
        body = "\n".join(
            [
                content.caption,
                "Precise values not established.",
                *[
                    f"{item.basis} ({'uncertain' if item.uncertain else 'claimed'}): {item.text}"
                    for item in content.observations
                ],
            ]
        )
    elif isinstance(content, Table):
        lines = [content.caption]
        headers = [cell for cell in content.cells if cell.role != "data"]
        for cell in sorted(content.cells, key=lambda value: (value.row, value.column)):
            if cell.role != "data":
                continue
            matched = [
                header.text
                for header in headers
                if (
                    header.role == "column_header"
                    and header.row < cell.row
                    and header.column <= cell.column < header.column + header.column_span
                )
                or (
                    header.role == "row_header"
                    and header.column < cell.column
                    and header.row <= cell.row < header.row + header.row_span
                )
            ]
            labels = " | ".join(matched) or "header unavailable"
            value = "missing" if cell.missing else cell.text or "empty"
            lines.append(
                f"Row {cell.row + 1}, column {cell.column + 1} [{labels}]: {value}"
                + (f"; unit={cell.unit}" if cell.unit else "; unit not specified")
                + (
                    f"; span={cell.row_span}x{cell.column_span}"
                    if cell.row_span > 1 or cell.column_span > 1
                    else ""
                )
                + ("; ambiguous" if cell.ambiguous else "")
            )
        lines.extend("Footnote: " + note for note in content.footnotes)
        body = "\n".join(lines)
    else:
        raise ValueError("unsupported evidence content")
    return prefix + "\n" + body
