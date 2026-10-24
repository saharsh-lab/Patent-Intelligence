// Turns an answer like "The pump runs [E1][E2].\n\n- item **bold** [?]" into
// structured blocks the UI renders safely (no HTML injection from model output).

export type Inline =
  | { kind: "text"; text: string }
  | { kind: "bold"; text: string }
  | { kind: "italic"; text: string }
  | { kind: "code"; text: string }
  | { kind: "citation"; label: string } // "E1"
  | { kind: "invalid-citation" }; // "[?]" — label the model invented

export type Block =
  | { kind: "paragraph"; inlines: Inline[]; raw: string }
  | { kind: "list"; items: Inline[][]; raws: string[]; ordered?: boolean }
  | { kind: "heading"; inlines: Inline[]; raw: string; level: number };

// [E1] · [?] · **bold** · `code` · *italic* / _italic_ (not inside words: snake_case stays)
const TOKEN = /\[(E\d+)\]|\[\?\]|\*\*([^*]+)\*\*|`([^`\n]+)`|(?<![\w*])\*(?!\s)([^*\n]+?)\*(?![\w*])|(?<!\w)_(?!\s)([^_\n]+?)_(?!\w)/g;

export function parseInline(text: string): Inline[] {
  const out: Inline[] = [];
  let last = 0;
  for (const match of text.matchAll(TOKEN)) {
    const index = match.index ?? 0;
    if (index > last) out.push({ kind: "text", text: text.slice(last, index) });
    if (match[1]) out.push({ kind: "citation", label: match[1] });
    else if (match[2]) out.push({ kind: "bold", text: match[2] });
    else if (match[3]) out.push({ kind: "code", text: match[3] });
    else if (match[4] || match[5]) out.push({ kind: "italic", text: (match[4] ?? match[5]) as string });
    else out.push({ kind: "invalid-citation" });
    last = index + match[0].length;
  }
  if (last < text.length) out.push({ kind: "text", text: text.slice(last) });
  return out;
}

const BULLET = /^\s*(?:[-*•]|\d+[.)])\s+/;
const NUMBERED = /^\s*\d+[.)]\s+/;
const HEADING = /^\s*(#{1,4})\s+(.+?)\s*#*\s*$/;

/** Paragraphs, bullet and numbered lists, and headings. A list may follow a line of text
 *  without a blank line ("Key points:\n- a\n- b"), as chat models often write it. */
export function parseAnswer(text: string): Block[] {
  const blocks: Block[] = [];
  for (const chunk of text.split(/\n\s*\n/)) {
    let paragraph: string[] = [];
    let list: string[] = [];
    let ordered = false;
    const endParagraph = () => {
      if (!paragraph.length) return;
      const raw = paragraph.join("\n"); // a single line break stays one (poems, addresses)
      blocks.push({ kind: "paragraph", inlines: parseInline(raw), raw });
      paragraph = [];
    };
    const endList = () => {
      if (!list.length) return;
      blocks.push({ kind: "list", items: list.map(parseInline), raws: list, ordered });
      list = [];
    };
    for (const line of chunk.split("\n").filter((l) => l.trim())) {
      const heading = line.match(HEADING);
      if (heading) {
        endParagraph();
        endList();
        blocks.push({ kind: "heading", level: heading[1].length, raw: heading[2], inlines: parseInline(heading[2]) });
      } else if (BULLET.test(line)) {
        endParagraph();
        if (!list.length) ordered = NUMBERED.test(line);
        list.push(line.replace(BULLET, ""));
      } else {
        endList();
        paragraph.push(line.trim());
      }
    }
    endParagraph();
    endList();
  }
  return blocks;
}

/** Remove the "Interpretation: ..." paragraph (shown separately in the UI). */
export function stripInterpretation(text: string): string {
  const match = text.match(/(?:^|\n\n|(?<=[.!?\]])[ \t]+)\**interpretation\**\s*:/i);
  return match?.index !== undefined ? text.slice(0, match.index).trim() : text;
}
