"use client";

import { useEffect, useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu, Istatistik } from "@/components/ortak";
import { api, gorselUrl } from "@/lib/api";
import type { TakipSonuc } from "@/lib/tipler";

function Indir({ yol, etiket }: { yol: string | null; etiket: string }) {
  if (!yol) return null;
  return (
    <a
      href={gorselUrl(yol)}
      download
      className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
    >
      {etiket}
    </a>
  );
}

export default function TakipSayfa() {
  const [dosya, setDosya] = useState<File | null>(null);
  const [aralik, setAralik] = useState(0.5);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<TakipSonuc | null>(null);
  const [ornekMi, setOrnekMi] = useState(false);
  const [hata, setHata] = useState("");
  const [durum, setDurum] = useState<{ trackastra: boolean } | null>(null);

  useEffect(() => {
    api.takipDurum().then(setDurum).catch(() => setDurum(null));
  }, []);

  async function calistir(fn: () => Promise<TakipSonuc>, ornek: boolean) {
    setYukleniyor(true);
    setHata("");
    try {
      setSonuc(await fn());
      setOrnekMi(ornek);
    } catch (e) {
      setHata((e as Error).message);
    } finally {
      setYukleniyor(false);
    }
  }

  function analizEt() {
    if (!dosya) return;
    const form = new FormData();
    form.append("dosya", dosya);
    form.append("kare_araligi_sn", String(aralik));
    calistir(() => api.takipAnaliz(form), false);
  }

  const enUzunIzler = sonuc
    ? [...sonuc.izler].sort((a, b) => b.sure_kare - a.sure_kare).slice(0, 12)
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Hücre Takibi (Cell Tracking)</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Zaman serisi görüntü yükleyin (MP4/AVI video, çok sayfalı TIFF veya kare
          görüntülerini içeren ZIP). Sistem her kareyi segmentler, hücreleri kareler
          arasında eşler, iz (track) kimlikleri atar; doğum, ölüm ve bölünme
          olaylarını çıkarır. Kaplamalı video, sayım grafiği ve CSV/JSON üretir.
        </p>
        {durum && (
          <p className="mt-1 text-xs text-slate-400">
            Transformer takibi (Trackastra):{" "}
            {durum.trackastra
              ? "etkin"
              : "kurulu değil — yerleşik IoU + Macar algoritması takibi kullanılıyor"}
          </p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <DosyaYukle
          onSec={(d) => {
            setDosya(d[0]);
            setSonuc(null);
          }}
          kabul=".mp4,.avi,.mov,.tif,.tiff,.zip"
          ipucu="MP4 / AVI · çok sayfalı TIFF · kare görüntüleri içeren ZIP"
        />
        <div className="kart space-y-3 p-4">
          <label className="block text-sm">
            <span className="text-slate-500 dark:text-slate-400">
              Kare aralığı: <strong>{aralik.toFixed(2)} sn</strong>
            </span>
            <input
              type="range"
              min={0.1}
              max={3}
              step={0.1}
              value={aralik}
              onChange={(e) => setAralik(Number(e.target.value))}
              className="mt-1 w-full"
            />
          </label>
          <button
            onClick={analizEt}
            disabled={!dosya || yukleniyor}
            className="w-full rounded-lg bg-marka-600 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
          >
            {yukleniyor ? "İşleniyor…" : "Takibi başlat"}
          </button>
          <button
            onClick={() => calistir(() => api.takipOrnek(), true)}
            disabled={yukleniyor}
            className="w-full rounded-lg border border-slate-200 py-2 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Örnek zaman serisi ile dene
          </button>
        </div>
      </div>

      {yukleniyor && (
        <IlerlemeCubugu etiket="Kareler çıkarılıyor, segmentleniyor ve izler eşleştiriliyor" />
      )}
      {hata && <HataKutusu mesaj={hata} />}

      {sonuc && (
        <div className="space-y-6">
          {ornekMi && (
            <span className="inline-block rounded-full bg-sky-100 px-3 py-1 text-xs font-semibold text-sky-800 dark:bg-sky-900/50 dark:text-sky-200">
              Örnek veri
            </span>
          )}

          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <Istatistik etiket="Kare sayısı" deger={sonuc.kare_sayisi} />
            <Istatistik
              etiket="Anlamlı iz"
              deger={sonuc.iz_sayisi}
              alt={`${sonuc.ham_iz_parcasi} ham parça`}
            />
            <Istatistik etiket="Bölünme olayı" deger={sonuc.bolunme_sayisi} />
            <Istatistik
              etiket="Hücre (ilk → son)"
              deger={`${sonuc.ilk_kare_hucre} → ${sonuc.son_kare_hucre}`}
            />
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {(sonuc.kaplama_gif || sonuc.kaplama_video) && (
              <figure className="kart overflow-hidden">
                <figcaption className="border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
                  İz kaplamalı zaman serisi
                </figcaption>
                {sonuc.kaplama_gif ? (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    src={gorselUrl(sonuc.kaplama_gif)}
                    alt="İz kaplamalı animasyon"
                    className="w-full bg-black object-contain"
                  />
                ) : (
                  <video
                    src={gorselUrl(sonuc.kaplama_video!)}
                    controls
                    loop
                    muted
                    className="w-full bg-black"
                  />
                )}
              </figure>
            )}
            {sonuc.grafik && (
              <figure className="kart overflow-hidden">
                <figcaption className="border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
                  Sayım ve iz uzunluğu
                </figcaption>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={gorselUrl(sonuc.grafik)}
                  alt="Takip grafiği"
                  className="w-full bg-white object-contain p-2 dark:bg-slate-950"
                />
              </figure>
            )}
          </div>

          {sonuc.kaplama_kareler.length > 0 && (
            <div className="kart p-4">
              <h3 className="mb-3 font-semibold">Kaplamalı kareler</h3>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-6">
                {sonuc.kaplama_kareler.map((k, i) => (
                  // eslint-disable-next-line @next/next/no-img-element
                  <img
                    key={i}
                    src={gorselUrl(k)}
                    alt={`Kare ${i}`}
                    className="rounded border border-slate-200 dark:border-slate-800"
                  />
                ))}
              </div>
            </div>
          )}

          <div className="grid gap-4 lg:grid-cols-2">
            <div className="kart overflow-x-auto p-4">
              <h3 className="mb-3 font-semibold">En uzun izler</h3>
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-1.5 pr-3">İz</th>
                    <th className="py-1.5 pr-3">Ebeveyn</th>
                    <th className="py-1.5 pr-3">Kareler</th>
                    <th className="py-1.5">Süre</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {enUzunIzler.map((z) => (
                    <tr key={z.id}>
                      <td className="py-1.5 pr-3 tabular-nums">#{z.id}</td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {z.parent_id ? `#${z.parent_id}` : "—"}
                      </td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {z.baslangic_kare}–{z.bitis_kare}
                      </td>
                      <td className="py-1.5 tabular-nums">{z.sure_kare} kare</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div className="kart p-4">
              <h3 className="mb-3 font-semibold">
                Bölünme olayları ({sonuc.bolunmeler.length})
              </h3>
              {sonuc.bolunmeler.length === 0 ? (
                <p className="text-sm text-slate-500">Bölünme tespit edilmedi.</p>
              ) : (
                <ul className="space-y-1 text-sm">
                  {sonuc.bolunmeler.map((b, i) => (
                    <li key={i} className="tabular-nums">
                      Kare {b.kare} (t={b.zaman_sn.toFixed(1)}s): #{b.parent} →{" "}
                      {b.cocuklar.map((c) => `#${c}`).join(" + ")}
                    </li>
                  ))}
                </ul>
              )}
            </div>
          </div>

          <div className="kart p-4">
            <h3 className="mb-2 font-semibold">Açıklama</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              {sonuc.aciklama}
            </p>
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-slate-400">İndir:</span>
            <Indir yol={sonuc.kaplama_video} etiket="MP4 (kaplamalı)" />
            <Indir yol={sonuc.grafik} etiket="PNG (grafik)" />
            <Indir yol={sonuc.csv_rapor} etiket="CSV (izler)" />
            <Indir yol={sonuc.json_rapor} etiket="JSON" />
          </div>
        </div>
      )}
    </div>
  );
}
