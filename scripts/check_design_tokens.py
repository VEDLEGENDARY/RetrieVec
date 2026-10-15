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


def check_contrast(tokens: str):
    """WCAG relative luminance from the CSS source, resolving aliases per theme."""
    values = dict(re.findall(r"(--[\w-]+)\s*:\s*([^;]+);", tokens))

    def resolve(name: str, dark: bool) -> str:
        value = values[name].strip()
        alias = re.fullmatch(r"var\((--[\w-]+)\)", value)
        if alias:
            return resolve(alias[1], dark)
        pair = re.fullmatch(r"light-dark\(\s*(#[\da-fA-F]{6}),\s*(#[\da-fA-F]{6})\s*\)", value)
        if pair:
            return pair[2 if dark else 1]
        if re.fullmatch(r"#[\da-fA-F]{6}", value):
            return value
        raise ValueError(f"Unsupported contrast color: {name} = {value}")

    def luminance(color: str) -> float:
        channels = [int(color[i : i + 2], 16) / 255 for i in (1, 3, 5)]
        linear = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
        return sum(c * weight for c, weight in zip(linear, (0.2126, 0.7152, 0.0722), strict=True))

    # Every allowed text role on every opaque reading surface, plus inverse actions.
    foregrounds = ("--ink", "--muted", "--brand", "--violet", "--danger", "--disabled-ink")
    surfaces = (
        "--canvas",
        "--surface",
        "--subtle",
        "--brand-soft",
        "--violet-soft",
        "--danger-soft",
        "--disabled-surface",
    )
    pairs = [(fg, bg) for fg in foregrounds for bg in surfaces]
    pairs += [("--on-action", "--action-background"), ("--on-action", "--action-hover")]
    minimum = (float("inf"), "")
    errors = []
    for dark in (False, True):
        for fg, bg in pairs:
            a, b = luminance(resolve(fg, dark)), luminance(resolve(bg, dark))
            ratio = (max(a, b) + 0.05) / (min(a, b) + 0.05)
            label = f"{'dark' if dark else 'light'} {fg} on {bg}"
            minimum = min(minimum, (ratio, label))
            if ratio < 4.5:
                errors.append(f"{label}: {ratio:.3f}:1 < 4.5:1")
    if errors:
        raise SystemExit("\n".join(errors))
    print(
        f"Text contrast: {len(pairs) * 2} pairs passed; minimum {minimum[0]:.3f}:1 ({minimum[1]})"
    )


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
    steps = set(re.findall(r"--t-(\d+)\s*:", tokens))
    if steps != {str(n) for n in range(7)}:
        errors.append("tokens.css must define --t-0 through --t-6")
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
    check_contrast(tokens)


if __name__ == "__main__":
    main()
