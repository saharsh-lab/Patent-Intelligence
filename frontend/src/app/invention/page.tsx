import type { Metadata } from "next";
import { Suspense } from "react";

import { InventionWorkspace } from "@/components/invention/InventionWorkspace";
import { PageHeader, Spinner } from "@/components/ui";

export const metadata: Metadata = { title: "Invention Analysis" };

export default function InventionPage() {
  return (
    <>
      <PageHeader
        title="Invention Analysis"
        description="Describe an invention (or pick an uploaded draft). The system splits it into technical features, finds the closest documents, and checks feature by feature where each one is disclosed, citing the passage. A technical comparison only: not an assessment of novelty or infringement."
      />
      {/* reads ?run= from the URL, which requires a Suspense boundary */}
      <Suspense fallback={<Spinner label="Loading…" />}>
        <InventionWorkspace />
      </Suspense>
    </>
  );
}
