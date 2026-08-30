/**
 * Kısa bir GIF demo için kare kare ekran görüntüsü alır.
 * Kareler docs/ekran-goruntuleri/gif-kareler/ altına yazılır; birleştirme
 * scripts/gif_birlestir.py (Pillow) ile yapılır.
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const DIZIN = path.join(KOK, "docs/ekran-goruntuleri/gif-kareler");
const TABAN = process.env.TABAN ?? "http://localhost:3000";
mkdirSync(DIZIN, { recursive: true });
const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1200, height: 760 } });
let n = 0;
const kare = async (t = 250) => {
  await p.screenshot({ path: path.join(DIZIN, `k${String(n++).padStart(2, "0")}.png`) });
  await bekle(t);
};

await p.goto(`${TABAN}/`, { waitUntil: "networkidle" });
await bekle(800);
await kare(500); await kare(500);

await p.goto(`${TABAN}/analiz`, { waitUntil: "networkidle" });
await bekle(500);
await kare(500);
await p.getByRole("button", { name: "Filamentli" }).click();
await kare(400); await kare(400);
await p.getByText("Tahmin edilen sınıf").waitFor({ timeout: 60000 });
await bekle(800);
await kare(600);
await p.mouse.wheel(0, 500);
await kare(600);
await p.mouse.wheel(0, 600);
await kare(600);

await p.goto(`${TABAN}/gecmis`, { waitUntil: "networkidle" });
await bekle(700);
await kare(700);

await p.goto(`${TABAN}/ayarlar`, { waitUntil: "networkidle" });
await bekle(700);
await kare(700);

await b.close();
console.log(`${n} kare yazıldı -> ${DIZIN}`);
