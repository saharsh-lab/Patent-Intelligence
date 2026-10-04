import { redirect } from "next/navigation";

/** The app opens in chat: the greeting and quick actions live in the new-chat screen. */
export default function Home() {
  redirect("/chat");
}
