"use client";

import { motion } from "framer-motion";
import { useState, type RefObject } from "react";

import { icons } from "@/components/icons";

// The same bar lives in the hero (centre) and in the results header (top). Both
// render a motion.form with one layoutId, so a submit makes the bar glide between
// the two positions instead of jumping.
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
        onSubmit();
      }}
      className={`relative flex w-full items-center gap-2 border bg-surface ${
        hero ? "rounded-[22px] p-2 pl-4" : "rounded-2xl p-1.5 pl-3.5"
      } ${focused ? "border-clay/60" : "border-line-strong"}`}
      style={{ boxShadow: "var(--shadow)" }}
    >
      {/* Focus glow: a pre-painted shadow layer that only changes opacity */}
      <span
        aria-hidden
        className="pointer-events-none absolute -inset-px rounded-[inherit] transition-opacity duration-300"
        style={{ opacity: focused ? 1 : 0, boxShadow: "0 0 0 4px rgb(217 119 87 / 0.14), 0 10px 34px -8px rgb(217 119 87 / 0.35)" }}
      />
      <icons.search className="shrink-0 text-muted" width={hero ? 20 : 17} height={hero ? 20 : 17} />
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
        className={`min-w-0 flex-1 bg-transparent outline-none focus-visible:outline-none placeholder:text-muted/80 ${hero ? "py-2.5 text-base md:text-[17px]" : "py-1.5 text-[15px]"}`}
      />
      <motion.button
        type="submit"
        disabled={busy || !value.trim()}
        whileTap={{ scale: 0.94 }}
        whileHover={{ scale: 1.03 }}
        transition={{ type: "spring", stiffness: 500, damping: 30 }}
        className={`flex shrink-0 items-center gap-1.5 rounded-xl bg-brand font-medium text-white disabled:cursor-not-allowed disabled:opacity-45 ${
          hero ? "px-4 py-2.5 text-sm md:px-5" : "px-3.5 py-2 text-sm"
        }`}
      >
        {busy ? "Searching" : "Search"}
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden className="hidden sm:block">
          <path d="M5 12h14M13 6l6 6-6 6" />
        </svg>
      </motion.button>
    </motion.form>
  );
}
