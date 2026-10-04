import type { Metadata } from "next";

import { WatchesWorkspace } from "@/components/watches/WatchesWorkspace";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Patent Watch" };

export default function WatchesPage() {
  return (
    <>
      <PageHeader
        title="Patent Watch"
        description="Saved searches that look for newly published patents. Each check asks the patent databases for publications since the last check, ranks new ones by similarity to your document, and imports the closest so you can analyse them."
      />
      <WatchesWorkspace />
    </>
  );
}
