import type { Metadata } from "next";

import { Landing } from "@/components/landing/Landing";

export const metadata: Metadata = { title: { absolute: "Patent Intelligence · Where patents meet proof" } };

/** The public front page; the app itself starts at /chat. */
export default function Home() {
  return <Landing />;
}
