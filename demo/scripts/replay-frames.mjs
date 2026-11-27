// One screenshot per step of the trace replay, for building a README GIF.
// Usage (after `npm run build`):  node scripts/replay-frames.mjs [outDir] [traceId ...]
// Default traces tell the story in about 25 frames: an attack that works, a defense that blocks it
// in English, and the same defense missing it in Hindi. Frames are numbered in playback order.
import { mkdirSync } from "node:fs";
import { resolve } from "node:path";
import { chromium } from "playwright-core";
import { preview } from "vite";

const [outArg, ...ids] = process.argv.slice(2);
const out = resolve(outArg ?? "shots/replay");
const traces = ids.length ? ids : ["en-owner-note-tool-output", "detector-en-blocked", "detector-hi-fails"];
mkdirSync(out, { recursive: true });

const server = await preview({ preview: { port: 4173, strictPort: true } });
const browser = await chromium.launch({ channel: "chrome" });
let n = 0;
try {
  const page = await browser.newPage({ viewport: { width: 960, height: 720 } });
  for (const id of traces) {
    await page.goto(`http://localhost:4173/agent-injection-eval/#/replay/${id}`);
    await page.waitForSelector(".player");
    await page.evaluate(() => window.scrollTo(0, document.querySelector(".controls")?.getBoundingClientRect().top + scrollY - 24));
    const total = await page.locator(".timeline > .step").count();
    for (let step = 0; step < total; step++) {
      n += 1;
      await page.screenshot({ path: resolve(out, `${String(n).padStart(3, "0")}.png`) });
      if (step < total - 1) await page.getByRole("button", { name: "Next" }).click();
    }
  }
  console.log(`${n} frames in ${out}`);
} finally {
  await browser.close();
  await new Promise((done) => server.httpServer.close(done));
}
