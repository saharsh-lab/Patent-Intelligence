import type { ReactNode } from "react";

/**
 * Wraps every page. A template remounts on each navigation, so the entrance
 * animation (and the staggered reveal of lists and table rows, see globals.css)
 * plays whenever the user moves to another page.
 */
export default function Template({ children }: { children: ReactNode }) {
  return <div className="page-enter flex min-h-full flex-col">{children}</div>;
}
