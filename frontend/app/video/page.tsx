"use client";

import { useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu } from "@/components/ortak";
import { ZamanSerisiGrafik } from "@/components/Grafikler";
import { SonucGorunumu } from "@/components/SonucGorunumu";
import { api } from "@/lib/api";
import type { VideoSonuc } from "@/lib/tipler";

const SEVIYE_SINIF: Record<string, string> = {
  bilgi: "border-emerald-300 bg-emerald-50 text-emerald-800 dark:border-emerald-800 dark:bg-emerald-950/40 dark:text-emerald-200",
  dikkat: "border-amber-300 bg-amber-50 text-amber-800 dark:border-amber-800 dark:bg-amber-950/40 dark:text-amber-200",
  kritik: "border-red-300 bg-red-50 text-red-800 dark:border-red-800 dark:bg-red-950/40 dark:text-red-200",
};

export default function VideoSayfa() {
  const [video, setVideo] = useState<File | null>(null);
  const [aralik, setAralik] = useState(2);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<VideoSonuc | null>(null);
  const [seciliIdx, setSeciliIdx] = useState(0);
  const [hata, setHata] = useState("");

  async function analizEt() {
    if (!video) return;
    setYukleniyor(true);
    setHata("");
    try {
      const form = new FormData();
      form.append("dosya", video);
      form.append("kare_araligi_sn", String(aralik));
      const y = await api.videoAnaliz(form);
      setSonuc(y);
      setSeciliIdx(0);
    } catch (e) {
      setHata((e as Error).message);
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Video / zaman serisi analizi</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          MP4 / AVI video yükleyin. Kareler belirli aralıklarla örneklenir; zamanla bakteri sayısı
          ve yoğunluk değişimi izlenir, aktivite kaybı gibi seri uyarıları üretilir.
        </p>
      </div>

      <DosyaYukle onSec={(d) => { setVideo(d[0]); setSonuc(null); }} kabul="video/mp4,video/x-msvideo,.mp4,.avi" ipucu="MP4, AVI" />
      <label className="flex items-center gap-3 text-sm">
        Kare örnekleme aralığı: <strong>{aralik.toFixed(1)} sn</strong>
        <input type="range" min={0.5} max={10} step={0.5} value={aralik} onChange={(e) => setAralik(Number(e.target.value))} className="w-48" />
      </label>
      <button
        onClick={analizEt}
        disabled={!video || yukleniyor}
        className="rounded-lg bg-marka-600 px-5 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
      >
        {yukleniyor ? "İşleniyor…" : "Videoyu analiz et"}
      </button>

      {yukleniyor && <IlerlemeCubugu etiket="Video kareleri çıkarılıyor ve kare kare analiz ediliyor" />}
      {hata && <HataKutusu mesaj={hata} />}

      {sonuc && (
        <div className="space-y-4">
          <div className="kart p-4 text-sm">{sonuc.ozet_aciklama}</div>

          {sonuc.seri_uyarilari.length > 0 && (
            <ul className="space-y-2">
              {sonuc.seri_uyarilari.map((u, i) => (
                <li key={i} className={`rounded-lg border px-3 py-2 text-sm ${SEVIYE_SINIF[u.seviye] ?? SEVIYE_SINIF.dikkat}`}>
                  <span className="font-semibold uppercase">[{u.seviye}]</span> {u.mesaj}
                </li>
              ))}
            </ul>
          )}

          <ZamanSerisiGrafik veri={sonuc.zaman_serisi} />

          <div className="flex flex-wrap gap-2">
            {sonuc.kareler.map((k, i) => (
              <button
                key={k.id}
                onClick={() => setSeciliIdx(i)}
                className={`rounded-lg border px-3 py-1.5 text-xs ${
                  i === seciliIdx ? "border-marka-500 bg-marka-50 dark:bg-marka-900/30" : "border-slate-200 dark:border-slate-700"
                }`}
              >
                t={k.kare_zamani_sn.toFixed(1)}s
              </button>
            ))}
          </div>
          {sonuc.kareler[seciliIdx] && <SonucGorunumu sonuc={sonuc.kareler[seciliIdx]} />}
        </div>
      )}
    </div>
  );
}
