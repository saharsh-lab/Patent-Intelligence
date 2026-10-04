// Render every *.mmd file in this folder to .svg (for the report) and .png (for slides).
//   cd docs/diagrams && npm install --no-save playwright && npx playwright install chromium
//   node render.mjs
// Or paste a .mmd file into https://mermaid.live and export it.
import { chromium } from "playwright";
import { readdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const dir = process.argv[2] ?? dirname(fileURLToPath(import.meta.url));
const browser = await chromium.launch();
const page = await browser.newPage({ deviceScaleFactor: 2, viewport: { width: 1600, height: 1200 } });
await page.setContent(
  `<html><body style="margin:0;background:#fff"><div id="out"></div>
   <script type="module">
     import mermaid from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs";
     mermaid.initialize({ startOnLoad: false, theme: "neutral", fontFamily: "Helvetica, Arial, sans-serif" });
     window.renderDiagram = async (code) => {
       const { svg } = await mermaid.render("d" + Math.random().toString(36).slice(2), code);
       document.getElementById("out").innerHTML = svg;
       return svg;
     };
   </script></body></html>`,
);
await page.waitForFunction(() => typeof window.renderDiagram === "function");
for (const file of readdirSync(dir).filter((f) => f.endsWith(".mmd")).sort()) {
  const code = readFileSync(join(dir, file), "utf8");
  const svg = await page.evaluate((c) => window.renderDiagram(c), code);
  const base = join(dir, file.replace(/\.mmd$/, ""));
  writeFileSync(`${base}.svg`, svg);
  await page.locator("#out svg").screenshot({ path: `${base}.png`, omitBackground: false });
  console.log("rendered", file);
}
await browser.close();
