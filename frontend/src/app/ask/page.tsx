import type { Metadata } from "next";
import { Suspense } from "react";

import { AskWorkspace } from "@/components/ask/AskWorkspace";
import { PageHeader, Spinner } from "@/components/ui";

export const metadata: Metadata = { title: "Research console" };

export default function AskPage() {
  return (
    <>
      <PageHeader
        title="Research console"
        description="Single questions with every retrieval and agent option exposed, for experiments. Answers are generated only from retrieved passages. Every statement cites its evidence; anything beyond the evidence is labelled as interpretation."
      />
      {/* AskWorkspace reads ?run= and ?doc= from the URL, which requires a Suspense boundary */}
      <Suspense fallback={<Spinner label="Loading…" />}>
        <AskWorkspace />
      </Suspense>
    </>
  );
}
