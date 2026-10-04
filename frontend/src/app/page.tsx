import { redirect } from "next/navigation";

/** The app opens on search (the animated single-question view); chat is one click away. */
export default function Home() {
  redirect("/search");
}
