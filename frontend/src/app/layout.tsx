import type { Metadata } from "next";
import { Geist_Mono, Inter } from "next/font/google";

import { AppShell } from "@/components/AppShell";

import "./globals.css";

// Fonts come from Google Fonts; next/font downloads them at build time and serves
// them from this origin, so the browser never contacts Google (keeps the CSP strict).
const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

export const metadata: Metadata = {
  title: { default: "Patent Intelligence", template: "%s · Patent Intelligence" },
  description: "Agentic RAG for multi-source patent intelligence with evidence-grounded answers.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} ${geistMono.variable}`} suppressHydrationWarning>
      <head>
        {/* Before the first paint: the saved theme (dark unless light or system was chosen) and
            whether the chat's left column is hidden */}
        <script
          dangerouslySetInnerHTML={{
            __html: `try{var d=document.documentElement,t=localStorage.getItem("theme");if(t==="light"||t==="system")d.dataset.theme=t;if(localStorage.getItem("chat-sidebar")==="hidden")d.dataset.chatSidebar="hidden"}catch(e){}`,
          }}
        />
      </head>
      <body>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
