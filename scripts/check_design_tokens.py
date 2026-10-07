"""Reject hardcoded theme/spacing declarations outside the shared token file."""

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DECLARATION = re.compile(
    r"(?:^|[;{])\s*(color|background-color|font-size|border-radius|box-shadow|"
    r"(?:animation|transition)-duration|gap|(?:row|column)-gap|"
    r"(?:margin|padding)(?:-[\w-]+)?)\s*:\s*([^;}]+)",
    re.M,
)
LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgb|hsl)a?\(")
MEASURE = re.compile(r"(?<![\w-])(?:\d*\.)?\d+(?:px|rem|em|vh|vw|ms|s|%)\b")


def violations(text: str, css: bool):
    for match in LITERAL.finditer(text):
        yield match.start(), "literal color"
    if css:
        for match in DECLARATION.finditer(text):
            value = re.sub(r"var\([^)]*\)", "", match[2])
            if MEASURE.search(value):
                yield match.start(), f"literal {match[1]}"
            if match[1] in ("color", "background-color") and value.strip() not in (
                "",
                "inherit",
                "initial",
                "unset",
                "transparent",
                "currentColor",
            ):
                yield match.start(), "untokenized color"
    else:
        for match in re.finditer(
            r"\b(?:color|backgroundColor|fontSize|margin|padding|gap)\s*:\s*([\"'][^\"']*[\"']|\d+)",
            text,
        ):
            value = match[1]
            if "var(" not in value and value not in ("0", '"inherit"'):
                yield match.start(), "inline design literal"


def main():
    errors = []
    tokens = (ROOT / "web/src/tokens.css").read_text(encoding="utf-8")
    roles = set(re.findall(r"--type-([\w-]+)\s*:", tokens))
    if roles != {"metadata", "supporting", "body", "subheading", "section-heading", "page-heading"}:
        errors.append("tokens.css must define exactly the six approved type roles")
    for path in sorted((ROOT / "web/src").rglob("*")):
        if path.suffix not in (".css", ".ts", ".tsx") or path.name == "tokens.css":
            continue
        text = path.read_text(encoding="utf-8")
        if path.suffix == ".tsx" and path.name != "ui.tsx":
            if re.search(r"<(?:button|input|select|textarea|label|dialog|details)\b", text):
                errors.append(f"{path.relative_to(ROOT)}: use shared UI primitives")
        for offset, reason in violations(text, path.suffix == ".css"):
            line = text[:offset].count("\n") + 1
            errors.append(f"{path.relative_to(ROOT)}:{line}: {reason}")
    if errors:
        raise SystemExit("\n".join(errors))
    print("Design token declarations: passed")


if __name__ == "__main__":
    main()
