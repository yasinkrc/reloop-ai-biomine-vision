"use client";

import { useState } from "react";
import { api, gorselUrl } from "@/lib/api";
import type { AnalizSonuc } from "@/lib/tipler";
import { RiskRozet } from "./ortak";

const SEVIYE_SINIF: Record<string, string> = {
  bilgi: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
  dikkat: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200",
  kritik: "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200",
};

function GorselKutu({ baslik, yol, bos }: { baslik: string; yol: string | null; bos?: string }) {
  return (
    <figure className="kart overflow-hidden">
      <figcaption className="border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
        {baslik}
      </figcaption>
      {yol ? (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={gorselUrl(yol)} alt={baslik} className="aspect-square w-full bg-slate-100 object-contain dark:bg-slate-950" />
      ) : (
        <div className="grid aspect-square place-items-center bg-slate-100 text-sm text-slate-400 dark:bg-slate-950">
          {bos ?? "Görsel yok"}
        </div>
      )}
    </figure>
  );
}

export function SonucGorunumu({ sonuc }: { sonuc: AnalizSonuc }) {
  const [disariDurum, setDisariDurum] = useState<string>("");
  const m = sonuc.morfoloji;

  async function disariAktar(bicim: "pdf" | "csv" | "json") {
    if (!sonuc.id) return;
    setDisariDurum(`${bicim.toUpperCase()} hazırlanıyor…`);
    try {
      const y = await fetch(api.disariAktarUrl, {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ analiz_idleri: [sonuc.id], bicim }),
      });
      if (!y.ok) throw new Error(await y.text());
      const blob = await y.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `biomine_analiz_${sonuc.id}.${bicim}`;
      a.click();
      URL.revokeObjectURL(url);
      setDisariDurum("");
    } catch (e) {
      setDisariDurum(`Dışa aktarma hatası: ${(e as Error).message}`);
    }
  }

  return (
    <div className="space-y-6">
      {/* Üst özet */}
      <div className="kart flex flex-wrap items-center justify-between gap-3 p-4">
        <div>
          <div className="text-xs uppercase tracking-wide text-slate-400">Tahmin edilen sınıf</div>
          <div className="text-xl font-bold">{sonuc.tahmin_sinifi}</div>
          <div className="text-sm text-slate-500 dark:text-slate-400">
            Güven oranı: <strong>%{sonuc.guven.toFixed(1)}</strong>
            {sonuc.desteklenmiyor && " · düşük güven / desteklenmeyen"}
            {sonuc.on_isleme.model_egitilmedi && " · model eğitilmedi (demo)"}
          </div>
        </div>
        <div className="flex items-center gap-3">
          <RiskRozet seviye={sonuc.risk_seviyesi} />
          {sonuc.id && (
            <div className="flex gap-1">
              {(["pdf", "csv", "json"] as const).map((b) => (
                <button
                  key={b}
                  onClick={() => disariAktar(b)}
                  className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  {b.toUpperCase()}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
      {disariDurum && <p className="text-sm text-slate-500">{disariDurum}</p>}

      {/* Görseller */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <GorselKutu baslik="Orijinal görüntü" yol={sonuc.orijinal_gorsel} />
        <GorselKutu baslik="İşaretlenmiş analiz" yol={sonuc.isaretli_gorsel} />
        <GorselKutu baslik="Grad-CAM ısı haritası" yol={sonuc.gradcam_gorsel} bos="Grad-CAM üretilmedi" />
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        {/* İlk 5 tahmin */}
        <div className="kart p-4">
          <h3 className="mb-3 font-semibold">İlk 5 olası sonuç</h3>
          <ul className="space-y-2">
            {sonuc.ilk_bes.map((o, i) => (
              <li key={i} className="space-y-1">
                <div className="flex justify-between text-sm">
                  <span>{o.sinif}</span>
                  <span className="tabular-nums text-slate-500">%{o.olasilik.toFixed(1)}</span>
                </div>
                <div className="h-2 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
                  <div className="h-full rounded-full bg-marka-500" style={{ width: `${Math.min(100, o.olasilik)}%` }} />
                </div>
              </li>
            ))}
          </ul>
        </div>

        {/* Morfoloji */}
        <div className="kart p-4">
          <h3 className="mb-3 font-semibold">Morfolojik ölçümler</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
            <dt className="text-slate-500">Toplam hücre sayısı</dt>
            <dd className="text-right font-medium">{m.hucre_sayisi}</dd>
            <dt className="text-slate-500">Görüntü kaplama oranı</dt>
            <dd className="text-right font-medium">%{m.kaplama_orani.toFixed(1)}</dd>
            <dt className="text-slate-500">Ortalama hücre alanı</dt>
            <dd className="text-right font-medium">{m.ort_hucre_alani.toFixed(0)} px²</dd>
            <dt className="text-slate-500">Ortalama uzunluk</dt>
            <dd className="text-right font-medium">{m.ort_uzunluk.toFixed(1)} px</dd>
            <dt className="text-slate-500">Ortalama genişlik</dt>
            <dd className="text-right font-medium">{m.ort_genislik.toFixed(1)} px</dd>
            <dt className="text-slate-500">Ortalama dairesellik</dt>
            <dd className="text-right font-medium">{m.ort_dairesellik.toFixed(2)}</dd>
            <dt className="text-slate-500">Baskın morfoloji</dt>
            <dd className="text-right font-medium">{m.baskin_morfoloji}</dd>
          </dl>
          <div className="mt-3 flex gap-2 text-xs">
            {Object.entries(m.morfoloji_dagilimi).map(([k, v]) => (
              <span key={k} className="rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">
                {k}: <strong>{v}</strong>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Uyarılar */}
      <div className="kart p-4">
        <h3 className="mb-3 font-semibold">Uyarılar ({sonuc.uyarilar.length})</h3>
        {sonuc.uyarilar.length === 0 ? (
          <p className="text-sm text-slate-500">Belirgin bir uyarı üretilmedi.</p>
        ) : (
          <ul className="space-y-2">
            {sonuc.uyarilar.map((u, i) => (
              <li key={i} className={`rounded-lg border px-3 py-2 text-sm ${SEVIYE_SINIF[u.seviye] ?? SEVIYE_SINIF.dikkat}`}>
                <span className="font-semibold uppercase">[{u.seviye}]</span> {u.mesaj}
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Yapay zeka açıklaması */}
      <div className="kart p-4">
        <h3 className="mb-2 font-semibold">Yapay zeka açıklaması</h3>
        <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">{sonuc.aciklama}</p>
        <p className="mt-2 text-xs text-slate-400">
          Segmentasyon yöntemi: {sonuc.on_isleme.segmentasyon_yontemi ?? "-"} · Bulanıklık skoru:{" "}
          {sonuc.on_isleme.bulaniklik_skoru?.toFixed(0)} · Parlaklık: {sonuc.on_isleme.parlaklik?.toFixed(0)}
        </p>
      </div>
    </div>
  );
}
