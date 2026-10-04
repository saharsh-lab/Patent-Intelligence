"use client";

import { motion } from "framer-motion";
import { useState, type RefObject } from "react";

// The same bar lives in the hero (centre) and in the results header (top). Both
// render a motion.form with one layoutId, so a submit makes the bar glide between
// the two positions instead of jumping.
// Look from the reference: square sheet, 1.5px ink border, hard 6px offset shadow
// that turns blue while focused (two pre-drawn shadows crossfade: opacity only).
export function SearchBar({
  value,
  onChange,
  onSubmit,
  busy,
  size,
  inputRef,
  autoFocus,
}: {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  busy: boolean;
  size: "hero" | "compact";
  inputRef?: RefObject<HTMLInputElement | null>;
  autoFocus?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const hero = size === "hero";
  return (
    <motion.form
      layoutId="search-bar"
      transition={{ type: "spring", stiffness: 260, damping: 32, mass: 0.9 }}
      role="search"
      onSubmit={(e) => {
        e.preventDefault();
        if (value.trim()) onSubmit();
        else inputRef?.current?.focus();
      }}
      className={`relative isolate flex w-full gap-2 border-[1.5px] bg-surface p-1.5 transition-colors duration-200 ${
        focused ? "border-cite" : "border-text"
      }`}
    >
      <span aria-hidden className="pointer-events-none absolute -inset-[1.5px] -z-10 transition-opacity duration-200" style={{ boxShadow: "var(--shadow-hard)", opacity: focused ? 0 : 1 }} />
      <span aria-hidden className="pointer-events-none absolute -inset-[1.5px] -z-10 transition-opacity duration-200" style={{ boxShadow: "var(--shadow-hard-focus)", opacity: focused ? 1 : 0 }} />
      <input
        ref={inputRef}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
        autoFocus={autoFocus}
        maxLength={2000}
        placeholder="Describe a technology or ask a question"
        aria-label="Search patents"
        className={`min-w-0 flex-1 bg-transparent px-3 outline-none placeholder:text-muted focus-visible:outline-none ${
          hero ? "py-3 text-[1.05rem]" : "py-2 text-[15px]"
        }`}
      />
      <motion.button
        type="submit"
        disabled={busy}
        whileTap={{ scale: 0.95 }}
        className={`shrink-0 bg-brand font-medium disabled:cursor-wait disabled:opacity-60 ${hero ? "px-[22px]" : "px-4 text-sm"}`}
      >
        {busy ? "Searching" : "Search"}
      </motion.button>
    </motion.form>
  );
}
