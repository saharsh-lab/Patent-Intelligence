// Turns an answer like "The pump runs [E1][E2].\n\n- item **bold** [?]" into
// structured blocks the UI renders safely (no HTML injection from model output).

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "citation"; label: string } // "E1"
  | { kind: "invalid-citation" }; // "[?]" — label the model invented

export type Block =
  | { kind: "paragraph"; inlines: Inline[]; raw: string }
  | { kind: "list"; items: Inline[][]; raws: string[] };

const TOKEN = /\[(E\d+)\]|\[\?\]|\*\*([^*]+)\*\*/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > last) out.push({ kind: "text", text: text.slice(last, index) });
    if (match[1]) out.push({ kind: "citation", label: match[1] });
    else if (match[2]) out.push({ kind: "bold", text: match[2] });
    else out.push({ kind: "invalid-citation" });
    last = index + match[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;

export function parseAnswer(text: string): Block[] {
  const blocks: Block[] = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    const lines = chunk.split("\n").filter((line) => line.trim());
    if (lines.length === 0) continue;
    if (lines.every((line) => BULLET.test(line))) {
      const raws = lines.map((l) => l.replace(BULLET, ""));
      blocks.push({ kind: "list", items: raws.map(parseInline), raws });
    } else {
      const raw = lines.join(" ");
      blocks.push({ kind: "paragraph", inlines: parseInline(raw), raw });
    }
  }
  return blocks;
}

/** Remove the "Interpretation: ..." paragraph (shown separately in the UI). */
export function stripInterpretation(text: string): string {
  const match = text.match(/(?:^|\n\n|(?<=[.!?\]])[ \t]+)\**interpretation\**\s*:/i);
  return match?.index !== undefined ? text.slice(0, match.index).trim() : text;
}
