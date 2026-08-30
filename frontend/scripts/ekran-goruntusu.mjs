/**
 * BioMine Vision — README için ekran görüntülerini üretir.
 * Çalışan frontend (localhost:3000) ve backend gerekir.
 *   node scripts/ekran-goruntusu.mjs
 */
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

const KOK = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const CIKTI = path.join(KOK, "docs/ekran-goruntuleri");
const TABAN = process.env.TABAN ?? "http://localhost:3000";
const VERI = path.join(KOK, "veri/demo");
mkdirSync(CIKTI, { recursive: true });

const bekle = (ms) => new Promise((r) => setTimeout(r, ms));

const tarayici = await chromium.launch();
const sayfa = await tarayici.newPage({ viewport: { width: 1440, height: 900 }, deviceScaleFactor: 2 });

async function cek(ad, { tamSayfa = true } = {}) {
  const yol = path.join(CIKTI, `${ad}.png`);
  await sayfa.screenshot({ path: yol, fullPage: tamSayfa });
  console.log("✓", ad);
}

// 1) Panel
await sayfa.goto(`${TABAN}/`, { waitUntil: "networkidle" });
await bekle(1200);
await cek("01-panel");

// 2) Tekli analiz — örnek çalıştır
await sayfa.goto(`${TABAN}/analiz`, { waitUntil: "networkidle" });
await sayfa.getByRole("button", { name: "Çubuk — yoğun" }).click();
await sayfa.getByText("Tahmin edilen sınıf").waitFor({ timeout: 60000 });
await bekle(1500);
await cek("02-tekli-analiz-sonuc");

// 3) İşaretli görüntü + Grad-CAM yakın plan
const gorseller = sayfa.locator("figure");
await gorseller.first().scrollIntoViewIfNeeded();
await bekle(400);
await cek("03-isaretli-ve-gradcam", { tamSayfa: false });

// 4) Toplu analiz
await sayfa.goto(`${TABAN}/toplu`, { waitUntil: "networkidle" });
await sayfa.locator('input[type=file]').setInputFiles(path.join(VERI, "ornek_parti.zip"));
await sayfa.getByRole("button", { name: /Toplu analiz et/ }).click();
await sayfa.getByText(/başarıyla analiz edildi/).waitFor({ timeout: 120000 });
await bekle(1500);
await cek("04-toplu-analiz");

// 5) Video / zaman serisi
await sayfa.goto(`${TABAN}/video`, { waitUntil: "networkidle" });
await sayfa.locator('input[type=file]').setInputFiles(path.join(VERI, "zaman_serisi.mp4"));
await sayfa.getByRole("button", { name: /Videoyu analiz et/ }).click();
await sayfa.getByText(/kare .* aralıkla analiz edildi/).waitFor({ timeout: 180000 });
await bekle(2000);
await cek("05-video-zaman-serisi");

// 6) Geçmiş
await sayfa.goto(`${TABAN}/gecmis`, { waitUntil: "networkidle" });
await bekle(1000);
await cek("06-gecmis");

// 7) Geçmiş detay (Grad-CAM + dağılım grafiği)
await sayfa.goto(`${TABAN}/gecmis/12`, { waitUntil: "networkidle" });
await bekle(1500);
await cek("07-analiz-detay");

// 8) Karşılaştırma
await sayfa.goto(`${TABAN}/karsilastir`, { waitUntil: "networkidle" });
const secimler = sayfa.locator("select");
await secimler.nth(0).selectOption({ index: 1 });
await secimler.nth(1).selectOption({ index: 4 });
await sayfa.getByRole("button", { name: "Karşılaştır" }).click();
await sayfa.getByText("Farklar (2. − 1.)").waitFor({ timeout: 30000 });
await bekle(1000);
await cek("08-karsilastirma");

// 9) Yönetim / eşikler
await sayfa.goto(`${TABAN}/ayarlar`, { waitUntil: "networkidle" });
await bekle(1000);
await cek("09-yonetim-esikler");

// 10) Koyu tema paneli
await sayfa.goto(`${TABAN}/`, { waitUntil: "networkidle" });
await sayfa.getByRole("button", { name: "Temayı değiştir" }).click();
await bekle(900);
await cek("10-panel-koyu-tema");

await tarayici.close();
console.log("Tüm ekran görüntüleri:", CIKTI);
