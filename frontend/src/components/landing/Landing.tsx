import Link from "next/link";
import type { ComponentType, SVGProps } from "react";

import { icons } from "@/components/icons";
import { LogoMark } from "@/components/search/Logo";

type Icon = ComponentType<SVGProps<SVGSVGElement>>;

// How one answer is made: the agent's real stages (app/agents/graph.py)
const STEPS = [
  { title: "Understand", text: "The planner reads your question and picks the tools it needs.", tone: "from-blue-600/35 border-blue-500/50", dot: "bg-blue-600" },
  { title: "Search", text: "Your library, patent filings and the web, searched at the same time.", tone: "from-fuchsia-600/30 border-fuchsia-500/50", dot: "bg-fuchsia-600" },
  { title: "Write", text: "A draft from the passages found, every sentence citing its source.", tone: "from-emerald-600/30 border-emerald-500/50", dot: "bg-emerald-600" },
  { title: "Check", text: "Each sentence is checked against the passage it cites.", tone: "from-orange-600/35 border-orange-500/50", dot: "bg-orange-600" },
  { title: "Rewrite", text: "Sentences the sources don't support are removed or corrected.", tone: "from-violet-600/35 border-violet-500/50", dot: "bg-violet-600" },
  { title: "Show the X-ray", text: "Open any sentence to see the passage it was checked against.", tone: "from-cyan-600/30 border-cyan-500/50", dot: "bg-cyan-600" },
];

const FEATURES: { icon: Icon; title: string; text: string; tags: string[]; href: string }[] = [
  { icon: icons.search, title: "Evidence-grounded chat", text: "Ask in plain language. Answers come from your documents, patent filings and the web, written live.", tags: ["📚 Cited sources", "⚡ Live answers", "💬 Follow-ups"], href: "/chat" },
  { icon: icons.bulb, title: "Invention analysis", text: "Describe an idea or upload a draft and find the patents with the closest technical overlap.", tags: ["🔍 Similar patents", "🧩 Technical overlap"], href: "/invention" },
  { icon: icons.sparkles, title: "Hallucination X-ray", text: "Every sentence is checked against its source and coloured by the verdict. Wrong words are underlined, and any text can be fact-checked against your sources.", tags: ["✅ Sentence verdicts", "≠ Contradictions", "🧪 Checker test", "🛠️ One-click fixes"], href: "/checker" },
  { icon: icons.map, title: "Patent landscape map", text: "See a field at a glance: patents grouped by meaning, with your invention placed among them.", tags: ["🗺️ Clusters", "⭐ Your invention"], href: "/landscape" },
  { icon: icons.bell, title: "Patent watch", text: "Follow a topic and see new filings as they are published.", tags: ["🔔 New filings", "📌 Saved searches"], href: "/watches" },
];

function Feature({ icon: Glyph, title, text, tags, href, tall = false }: (typeof FEATURES)[number] & { tall?: boolean }) {
  return (
    <Link
      href={href}
      className={`glass group flex flex-col rounded-3xl p-8 transition-colors hover:border-line-strong ${tall ? "h-full justify-center md:p-10" : ""}`}
    >
      <span className="grid h-11 w-11 place-items-center rounded-xl border border-line bg-surface-2 text-accent">
        <Glyph width={20} height={20} />
      </span>
      <h3 className="mt-6 text-2xl font-bold tracking-tight">{title}</h3>
      <p className="mt-3 leading-relaxed text-muted">{text}</p>
      <div className="mt-5 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <span key={tag} className="rounded-lg bg-surface-2 px-2.5 py-1 text-xs font-semibold">
            {tag}
          </span>
        ))}
      </div>
    </Link>
  );
}

const PILL = "press inline-flex items-center gap-2 rounded-full px-7 py-3.5 text-[0.95rem] font-semibold transition";

/** The public front page, after the reference site's home page. */
export function Landing() {
  return (
    <div className="overflow-x-clip">
      {/* Hero */}
      <section className="relative px-4 pt-[14vh] pb-24 text-center">
        <div aria-hidden className="pointer-events-none absolute inset-x-0 top-0 -z-10 h-[70vh] bg-glow" />
        <LogoMark size={56} draw className="mx-auto mb-6 text-text" />
        <h1 className="pi-line mx-auto max-w-5xl text-[clamp(2.6rem,7vw,4.6rem)] leading-[1.02] font-bold tracking-[-0.035em]">
          <span>Where patents meet proof</span>
        </h1>
        <p className="pi-in mx-auto mt-6 max-w-2xl text-lg font-medium text-muted md:text-xl" style={{ animationDelay: "0.2s" }}>
          Agentic RAG for patent research: answers from your documents, patent filings and the web, with every sentence
          linked to its source and checked.
        </p>
        <div className="pi-in mt-10 flex flex-wrap justify-center gap-3" style={{ animationDelay: "0.35s" }}>
          <Link href="/chat" className={`${PILL} bg-brand shadow-[0_0_0_4px_var(--line)] hover:opacity-90`}>
            Start researching <icons.arrowRight width={17} height={17} />
          </Link>
          <Link href="/landscape" className={`${PILL} border border-line-strong hover:bg-surface-2`}>
            Map a field
          </Link>
        </div>
      </section>

      {/* The product, tilted */}
      <section className="px-4 pt-16 pb-24 text-center">
        <h2 className="mx-auto max-w-3xl text-[clamp(2rem,4.5vw,3rem)] leading-tight">
          Your personal
          <br />
          <span className="text-gradient">patent analyst</span>
        </h2>
        <p className="mx-auto mt-4 max-w-xl text-muted">Watch it search, write and check each answer, live, with every source one click away.</p>
        <div className="mx-auto mt-14 max-w-5xl [perspective:1800px]">
          <div className="lp-tilt rounded-[28px] border border-line bg-surface p-2.5 shadow-hard">
            {/* eslint-disable-next-line @next/next/no-img-element -- a static screenshot */}
            <img
              src="/landing/chat.png"
              alt="The chat: an answer with numbered sources, every sentence checked against them"
              width={1440}
              height={900}
              className="w-full rounded-[20px] border border-line"
            />
          </div>
        </div>
      </section>

      {/* How it works */}
      <section className="py-24">
        <div className="px-4 text-center">
          <span className="inline-flex items-center gap-1.5 rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold">
            <icons.layers width={13} height={13} /> How an answer is made
          </span>
          <h2 className="mt-4 text-[clamp(2rem,4.5vw,3rem)] leading-tight">From question to checked answer</h2>
          <p className="mx-auto mt-3 max-w-2xl text-muted">An agent that plans, searches and verifies, instead of a model that just writes.</p>
        </div>
        <div className="lp-marquee-mask mt-14 overflow-hidden">
          <ol className="lp-marquee flex w-max gap-5 px-3">
            {[...STEPS, ...STEPS].map((step, i) => (
              <li
                key={i}
                aria-hidden={i >= STEPS.length}
                className={`flex w-[380px] shrink-0 flex-col justify-between gap-6 rounded-3xl border bg-gradient-to-br to-transparent p-7 ${step.tone}`}
              >
                <p className="text-lg leading-snug font-semibold">{step.text}</p>
                <div className="flex items-end justify-between border-t border-line pt-5">
                  <span>
                    <span className="block text-sm font-semibold text-muted">Step {(i % STEPS.length) + 1}</span>
                    <span className="block font-semibold">{step.title}</span>
                  </span>
                  <span className={`grid h-12 w-12 place-items-center rounded-full text-lg font-bold text-white shadow-lg ${step.dot}`}>
                    {(i % STEPS.length) + 1}
                  </span>
                </div>
              </li>
            ))}
          </ol>
        </div>
      </section>

      {/* What you can do */}
      <section className="mx-auto max-w-7xl px-4 py-24 md:px-8">
        <div className="text-center">
          <span className="inline-flex rounded-full border border-line bg-surface px-3 py-1 text-xs font-semibold">What you can do</span>
          <h2 className="mt-4 text-[clamp(2rem,4.5vw,3rem)] leading-tight">Everything for patent research</h2>
        </div>
        <div className="mt-14 grid gap-6 lg:grid-cols-3">
          <div className="grid gap-6">
            <Feature {...FEATURES[0]} />
            <Feature {...FEATURES[1]} />
          </div>
          <Feature {...FEATURES[2]} tall />
          <div className="grid gap-6">
            <Feature {...FEATURES[3]} />
            <Feature {...FEATURES[4]} />
          </div>
        </div>
      </section>

      {/* Call to action */}
      <section className="border-t border-line bg-surface/40 px-4 py-24 text-center">
        <h2 className="text-[clamp(1.9rem,4vw,2.6rem)] leading-tight">Take control of your patent research</h2>
        <p className="mx-auto mt-3 max-w-xl text-muted">Ask your first question. Every answer shows where it came from.</p>
        <div className="mt-9 flex flex-wrap justify-center gap-3">
          <Link href="/chat" className={`${PILL} bg-brand hover:opacity-90`}>
            <icons.chat width={17} height={17} /> Start a chat
          </Link>
          <Link href="/invention" className={`${PILL} border border-line-strong hover:bg-surface-2`}>
            Check an idea
          </Link>
        </div>
        <p className="mt-16 text-xs text-muted">
          Research assistance only: reports technical similarity and evidence from sources. Not legal advice.
        </p>
      </section>
    </div>
  );
}
