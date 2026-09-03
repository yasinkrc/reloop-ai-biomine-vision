import type {
  AnalizSonuc,
  AyarKaydi,
  GecmisKaydi,
  GenomSonuc,
  Saglik,
  TakipSonuc,
  TopluSonuc,
  VideoSonuc,
} from "./tipler";

// Tarayıcıda göreli yollar (next.config.js rewrites üzerinden backend'e proxy'lenir).
const TABAN = process.env.NEXT_PUBLIC_API_TABAN ?? "";

async function istek<T>(yol: string, sec?: RequestInit): Promise<T> {
  const y = await fetch(`${TABAN}${yol}`, sec);
  if (!y.ok) {
    let mesaj = `${y.status} ${y.statusText}`;
    try {
      const govde = await y.json();
      if (govde?.detail) mesaj = typeof govde.detail === "string" ? govde.detail : JSON.stringify(govde.detail);
    } catch {
      /* yoksay */
    }
    throw new Error(mesaj);
  }
  return y.json() as Promise<T>;
}

export function gorselUrl(goreli: string | null | undefined): string {
  if (!goreli) return "";
  return `${TABAN}/veri/${goreli}`.replace(/([^:]\/)\/+/g, "$1");
}

export const api = {
  saglik: () => istek<Saglik>("/api/saglik"),

  gorselAnaliz: (form: FormData) =>
    istek<AnalizSonuc>("/api/analiz/gorsel", { method: "POST", body: form }),

  topluAnaliz: (form: FormData) =>
    istek<TopluSonuc>("/api/analiz/toplu", { method: "POST", body: form }),

  videoAnaliz: (form: FormData) =>
    istek<VideoSonuc>("/api/analiz/video", { method: "POST", body: form }),

  ornekAnaliz: (ad: string) =>
    istek<AnalizSonuc>(`/api/analiz/ornek?ad=${encodeURIComponent(ad)}`, { method: "POST" }),

  gecmis: (params: { limit?: number; offset?: number; sadece_riskli?: boolean } = {}) => {
    const q = new URLSearchParams();
    if (params.limit) q.set("limit", String(params.limit));
    if (params.offset) q.set("offset", String(params.offset));
    if (params.sadece_riskli) q.set("sadece_riskli", "true");
    return istek<GecmisKaydi[]>(`/api/gecmis?${q.toString()}`);
  },

  gecmisGetir: (id: number) => istek<AnalizSonuc>(`/api/gecmis/${id}`),
  gecmisSil: (id: number) =>
    fetch(`${TABAN}/api/gecmis/${id}`, { method: "DELETE" }).then((y) => y.ok),

  karsilastir: (a: number, b: number) =>
    istek<{ birinci: AnalizSonuc; ikinci: AnalizSonuc; farklar: Record<string, number>; yorum: string }>(
      "/api/karsilastir",
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ analiz_id_1: a, analiz_id_2: b }),
      },
    ),

  ayarlar: () => istek<AyarKaydi[]>("/api/ayarlar"),
  ayarGuncelle: (anahtar: string, deger: number) =>
    istek<AyarKaydi>(`/api/ayarlar/${anahtar}`, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ deger }),
    }),
  desteklenenSiniflar: () =>
    istek<{ siniflar: { anahtar: string; etiket: string }[]; not: string }>(
      "/api/ayarlar/siniflar",
    ),

  // --- CRISPR-Cas / genom ---
  genomAnaliz: (form: FormData) =>
    istek<GenomSonuc>("/api/genom/analiz", { method: "POST", body: form }),
  genomOrnek: () => istek<GenomSonuc>("/api/genom/ornek", { method: "POST" }),
  genomOrnekCrispr: () =>
    istek<GenomSonuc>("/api/genom/ornek-crispr", { method: "POST" }),
  genomDurum: () =>
    istek<{
      cctyper: boolean;
      skani: boolean;
      prodigal: boolean;
      mmseqs: boolean;
      referans_genom_sayisi: number;
    }>("/api/genom/durum"),

  // --- Hücre takibi ---
  takipAnaliz: (form: FormData) =>
    istek<TakipSonuc>("/api/takip/analiz", { method: "POST", body: form }),
  takipOrnek: () => istek<TakipSonuc>("/api/takip/ornek", { method: "POST" }),
  takipDurum: () => istek<{ trackastra: boolean }>("/api/takip/durum"),

  disariAktarUrl: `${TABAN}/api/disari-aktar`,
};
