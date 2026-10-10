import { redirect } from "next/navigation";

/** Search and chat are one page now (2026-10-11); old /search links land on a new chat. */
export default function SearchPage() {
  redirect("/chat");
}
