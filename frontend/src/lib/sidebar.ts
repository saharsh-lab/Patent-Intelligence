// The chat's left column can be hidden (the panel button, or Ctrl/⌘+B). The choice is
// kept in this browser and applied before first paint (script in layout.tsx), through
// html[data-chat-sidebar="hidden"], so a hidden column never flashes open on load.
import { useSyncExternalStore } from "react";

const KEY = "chat-sidebar";
const listeners = new Set<() => void>();

export function sidebarHidden(): boolean {
  return typeof document !== "undefined" && document.documentElement.dataset.chatSidebar === "hidden";
}

export function setSidebarHidden(hidden: boolean) {
  const root = document.documentElement;
  if (hidden) root.dataset.chatSidebar = "hidden";
  else delete root.dataset.chatSidebar;
  try {
    if (hidden) localStorage.setItem(KEY, "hidden");
    else localStorage.removeItem(KEY);
  } catch {
    // private mode: the choice lasts for this page only
  }
  listeners.forEach((notify) => notify());
}

export function useSidebarHidden(): boolean {
  return useSyncExternalStore(
    (notify) => {
      listeners.add(notify);
      return () => listeners.delete(notify);
    },
    sidebarHidden,
    () => false, // server render: shown
  );
}
