import type { Metadata } from "next";

import { SearchExperience } from "@/components/search/SearchExperience";

export const metadata: Metadata = { title: "Search" };

/** Single-question patent search: one answer with numbered, linked sources. */
export default function SearchPage() {
  return <SearchExperience />;
}
