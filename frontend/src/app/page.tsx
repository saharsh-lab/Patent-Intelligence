import { redirect } from "next/navigation";

/** The app opens on the one asking page: a new chat with the search-style start screen. */
export default function Home() {
  redirect("/chat");
}
