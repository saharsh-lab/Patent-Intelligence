import type { Metadata } from "next";
import { Suspense } from "react";

import { EvaluationWorkspace } from "@/components/evaluation/EvaluationWorkspace";
import { PageHeader, Spinner } from "@/components/ui";

export const metadata: Metadata = { title: "Evaluation" };

export default function EvaluationPage() {
  return (
    <>
      <PageHeader
        title="Evaluation"
        description="Results of experiments run from the command line on a labelled question set. Means are shown with 95% bootstrap confidence intervals; differences count only when the interval excludes zero."
      />
      {/* reads ?r=<experiment>/<run> from the URL, which requires a Suspense boundary */}
      <Suspense fallback={<Spinner label="Loading…" />}>
        <EvaluationWorkspace />
      </Suspense>
    </>
  );
}
