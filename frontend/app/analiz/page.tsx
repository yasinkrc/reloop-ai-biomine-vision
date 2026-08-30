"use client";

import { useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu } from "@/components/ortak";
import { HucreDagilimGrafik } from "@/components/Grafikler";
import { SonucGorunumu } from "@/components/SonucGorunumu";
import { api } from "@/lib/api";
import type { AnalizSonuc } from "@/lib/tipler";

const ORNEKLER = [
  ["cubuk_bakteri_yogun", "Çubuk — yoğun"],
  ["kok_bakteri_kume", "Kok — küme"],
  ["filamentli_organizma", "Filamentli"],
  ["biyofilm_matriks", "Biyofilm"],
  ["karisik_kultur", "Karışık kültür"],
  ["dusuk_biyokutle", "Düşük biyokütle"],
];

export default function TekliAnaliz() {
  const [dosya, setDosya] = useState<File | null>(null);
  const [onIzleme, setOnIzleme] = useState<string>("");
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<AnalizSonuc | null>(null);
  const [hata, setHata] = useState("");

  const [gradcam, setGradcam] = useState(true);
  const [gurultu, setGurultu] = useState(true);
  const [kontrast, setKontrast] = useState(true);
  const [omnipose, setOmnipose] = useState(true);

  function secildi(dosyalar: File[]) {
    const d = dosyalar[0];
    setDosya(d);
    setOnIzleme(URL.createObjectURL(d));
    setSonuc(null);
    setHata("");
  }

  async function analizEt() {
    if (!dosya) return;
    setYukleniyor(true);
    setHata("");
    try {
      const form = new FormData();
      form.append("dosya", dosya);
      form.append("gradcam", String(gradcam));
      form.append("gurultu_azaltma", String(gurultu));
      form.append("kontrast_iyilestirme", String(kontrast));
      form.append("omnipose_kullan", String(omnipose));
      setSonuc(await api.gorselAnaliz(form));
    } catch (e) {
      setHata((e as Error).message);
    } finally {
      setYukleniyor(false);
    }
  }

  async function ornekCalistir(ad: string) {
    setYukleniyor(true);
    setHata("");
    setDosya(null);
    setOnIzleme("");
    try {
      setSonuc(await api.ornekAnaliz(ad));
    } catch (e) {
      setHata((e as Error).message);
    } finally {
      setYukleniyor(false);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Tekli görüntü analizi</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Bir mikroskop görüntüsü (JPG / PNG / TIFF) yükleyin; sistem segmentasyon, sayım,
          morfoloji, sınıflandırma, Grad-CAM ve uyarı üretir.
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <DosyaYukle onSec={secildi} ipucu="JPG, PNG, TIFF · en fazla 200 MB" />
          {onIzleme && (
            // eslint-disable-next-line @next/next/no-img-element
            <img src={onIzleme} alt="Ön izleme" className="max-h-72 rounded-lg border border-slate-200 object-contain dark:border-slate-800" />
          )}
          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-slate-400">Örnek verilerle dene:</span>
            {ORNEKLER.map(([ad, etiket]) => (
              <button
                key={ad}
                onClick={() => ornekCalistir(ad)}
                className="rounded-full border border-slate-200 px-3 py-1 text-xs hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
              >
                {etiket}
              </button>
            ))}
          </div>
        </div>

        <div className="kart space-y-3 p-4">
          <h2 className="font-semibold">Analiz seçenekleri</h2>
          {[
            ["Grad-CAM ısı haritası", gradcam, setGradcam],
            ["Gürültü azaltma", gurultu, setGurultu],
            ["Kontrast iyileştirme (CLAHE)", kontrast, setKontrast],
            ["Omnipose segmentasyonu (varsa)", omnipose, setOmnipose],
          ].map(([etiket, deger, set]) => (
            <label key={etiket as string} className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={deger as boolean}
                onChange={(e) => (set as (v: boolean) => void)(e.target.checked)}
                className="h-4 w-4 rounded"
              />
              {etiket as string}
            </label>
          ))}
          <button
            onClick={analizEt}
            disabled={!dosya || yukleniyor}
            className="w-full rounded-lg bg-marka-600 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
          >
            {yukleniyor ? "Analiz ediliyor…" : "Analiz et"}
          </button>
        </div>
      </div>

      {yukleniyor && <IlerlemeCubugu etiket="Görüntü işleniyor, segmentasyon ve model çıkarımı yapılıyor" />}
      {hata && <HataKutusu mesaj={hata} />}
      {sonuc && (
        <>
          <SonucGorunumu sonuc={sonuc} />
          {sonuc.hucreler.length > 0 && <HucreDagilimGrafik sonuc={sonuc} />}
        </>
      )}
    </div>
  );
}
