// Screenshots of every view at 360, 768 and 1440 px, plus a horizontal-overflow check.
// Usage (after `npm run build`):  node scripts/capture.mjs [outDir]
// Uses the Chrome already installed on the machine (no browser download) and Vite's preview server.
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright-core";
import { preview } from "vite";

const out = resolve(process.argv[2] ?? "shots");
mkdirSync(out, { recursive: true });

const widths = [360, 768, 1440];
const routes = [
  ["overview", "overview"],
  ["heatmap", "heatmap"],
  ["defenses", "defenses"],
  ["replay", "replay/detector-hi-fails"],
  ["how", "how"],
];

const server = await preview({ preview: { port: 4173, strictPort: true } });
const base = "http://localhost:4173/agent-injection-eval/";
const browser = await chromium.launch({ channel: "chrome" });
let overflow = 0;
try {
  for (const width of widths) {
    const page = await browser.newPage({ viewport: { width, height: 900 } });
    for (const [name, route] of routes) {
      await page.goto(`${base}#/${route}`);
      await page.waitForSelector("main h1");
      await page.waitForLoadState("networkidle");
      if (name === "replay") await page.waitForSelector(".player");
      const wide = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth);
      if (wide > 0) {
        overflow += 1;
        console.error(`OVERFLOW ${name} @${width}px: page is ${wide}px wider than the viewport`);
      }
      await page.screenshot({ path: resolve(out, `${width}-${name}.png`), fullPage: true });
      console.log(`${width}px ${name}: ok`);
    }
    await page.close();
  }
} finally {
  await browser.close();
  await new Promise((done) => server.httpServer.close(done));
}
if (overflow > 0) process.exit(1);
