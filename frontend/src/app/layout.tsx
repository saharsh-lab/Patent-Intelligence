import type { Metadata } from "next";
import { Geist_Mono, Newsreader, Schibsted_Grotesk } from "next/font/google";

import { AppShell } from "@/components/AppShell";

import "./globals.css";

// Fonts come from Google Fonts; next/font downloads them at build time and serves
// them from this origin, so the browser never contacts Google (keeps the CSP strict).
const newsreader = Newsreader({ variable: "--font-newsreader", subsets: ["latin"], style: ["normal", "italic"], axes: ["opsz"] });
const schibsted = Schibsted_Grotesk({ variable: "--font-schibsted", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Patent Intelligence", template: "%s · Patent Intelligence" },
  description: "Agentic RAG for multi-source patent intelligence with evidence-grounded answers.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${newsreader.variable} ${schibsted.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Apply the saved theme before the first paint (no light flash in dark mode) */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var t=localStorage.getItem("theme");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`,
          }}
        />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
