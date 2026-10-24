import type { ReactNode } from "react";

import type { Block } from "@/lib/citations";

/** Answer text as blocks (paragraphs, bullet and numbered lists, headings), each line drawn
 *  by `line` (plain, with citation chips, or in X-ray colours). `tail` follows the last line:
 *  the typing caret while an answer is written. */
export function AnswerBlocks({ blocks, line, tail = null }: { blocks: Block[]; line: (raw: string) => ReactNode; tail?: ReactNode }) {
  const last = blocks.length - 1;
  return (
    <>
      {blocks.map((block, i) => {
        const end = i === last ? tail : null;
        if (block.kind === "heading") {
          const Heading = block.level <= 2 ? "h3" : "h4";
          return (
            <Heading key={i} className="pt-1 font-sans text-[0.98rem] leading-snug font-semibold">
              {line(block.raw)}
              {end}
            </Heading>
          );
        }
        if (block.kind === "list") {
          const List = block.ordered ? "ol" : "ul";
          return (
            <List key={i} className={`${block.ordered ? "list-decimal" : "list-disc"} space-y-1 pl-5 marker:text-cite`}>
              {block.raws.map((raw, j) => (
                <li key={j}>
                  {line(raw)}
                  {j === block.raws.length - 1 ? end : null}
                </li>
              ))}
            </List>
          );
        }
        return (
          <p key={i} className="whitespace-pre-line">
            {line(block.raw)}
            {end}
          </p>
        );
      })}
    </>
  );
}
