import type { Metadata } from "next";

import { LandscapeWorkspace } from "@/components/landscape/LandscapeWorkspace";
import { PageHeader } from "@/components/ui";

export const metadata: Metadata = { title: "Landscape Map" };

export default function LandscapePage() {
  return (
    <>
      <PageHeader
        title="Landscape Map"
        description="See a technology area at a glance: every patent found for a topic is placed by the meaning of its title and abstract, so similar inventions sit together and form groups. Add your invention to see which patents are closest. Nothing is imported."
      />
      <LandscapeWorkspace />
    </>
  );
}
