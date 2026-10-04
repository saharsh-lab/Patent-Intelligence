"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";
import { useSWRConfig } from "swr";

import { icons } from "@/components/icons";
import { chat } from "@/lib/chat";

/** "Ask about this" anywhere in the library: a new chat with the item already attached. */
export function StartChatButton({
  documentId,
  patentId,
  label = "Ask about it",
}: {
  documentId?: string;
  patentId?: string;
  label?: string;
}) {
  const router = useRouter();
  const { mutate } = useSWRConfig();
  const [pending, setPending] = useState(false);

  async function start() {
    setPending(true);
    try {
      const conversation = await chat.create();
      await chat.attachSource(conversation.id, documentId ? { document_id: documentId } : { patent_id: patentId });
      await mutate("/conversations");
      router.push(`/chat/${conversation.id}`);
    } catch {
      setPending(false);
    }
  }

  return (
    <button
      type="button"
      onClick={start}
      disabled={pending}
      className="inline-flex items-center gap-1.5 text-sm font-medium text-accent hover:underline disabled:opacity-60"
    >
      <icons.chat width={14} height={14} />
      {pending ? "Opening chat…" : label}
    </button>
  );
}
