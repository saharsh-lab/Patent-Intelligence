import type { Metadata } from "next";

import { CheckerWorkspace } from "@/components/checker/CheckerWorkspace";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Fact Checker" };

export default function CheckerPage() {
  return (
    <>
      <PageHeader
        title="Fact Checker"
        description="Paste any text, such as an answer from another AI assistant or your own draft, and every sentence is checked against your documents and patents. Wrong words are underlined, each sentence opens the passage it was checked against, and flagged sentences can be removed or rewritten from the source."
      />
      <CheckerWorkspace />
    </>
  );
}
