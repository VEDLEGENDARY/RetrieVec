export type HighlightPart = { text: string; highlighted: boolean };

/** Plain segments only: passage text is never interpreted as HTML. */
export function highlightPassage(text: string, query: string): HighlightPart[] {
  const terms = [
    ...new Set(
      query.match(/[\p{L}\p{N}]+/gu)?.map((word) => word.toLocaleLowerCase()) ??
        [],
    ),
  ]
    .sort((a, b) => b.length - a.length)
    .slice(0, 64);
  if (!terms.length) return [{ text, highlighted: false }];
  const pattern = new RegExp(
    `(?<![\\p{L}\\p{N}])(?:${terms.map((term) => term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})(?![\\p{L}\\p{N}])`,
    "giu",
  );
  const parts: HighlightPart[] = [];
  let start = 0;
  for (const match of text.matchAll(pattern)) {
    if (match.index! > start)
      parts.push({ text: text.slice(start, match.index), highlighted: false });
    parts.push({ text: match[0], highlighted: true });
    start = match.index! + match[0].length;
  }
  if (start < text.length || !parts.length)
    parts.push({ text: text.slice(start), highlighted: false });
  return parts;
}
