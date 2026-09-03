"use client";

import { useEffect, useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu, Istatistik } from "@/components/ortak";
import { api, gorselUrl } from "@/lib/api";
import type { GenomSonuc } from "@/lib/tipler";

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

export default function CrisprSayfa() {
  const [dosya, setDosya] = useState<File | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<GenomSonuc | null>(null);
  const [ornekMi, setOrnekMi] = useState(false);
  const [hata, setHata] = useState("");
  const [durum, setDurum] = useState<{ cctyper: boolean; skani: boolean } | null>(null);

  useEffect(() => {
    api.genomDurum().then(setDurum).catch(() => setDurum(null));
  }, []);

  async function calistir(fn: () => Promise<GenomSonuc>, ornek: boolean) {
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
    calistir(() => api.genomAnaliz(form), false);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Bakteriyel CRISPR-Cas Analizi</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          FASTA / GenBank / GFF bakteriyel DNA yükleyin. Sistem en yakın tür/suşu
          bulur, CRISPR dizilerini ve Cas gen adaylarını çıkarır, CRISPR-Cas tipini
          belirler, aralayıcı (spacer) sayılarını gösterir ve genom + CRISPR lokus
          haritası üretir. Sonuç PNG, PDF, HTML, CSV ve JSON olarak indirilebilir.
        </p>
        {durum && (
          <p className="mt-1 text-xs text-slate-400">
            CRISPRCasTyper:{" "}
            {durum.cctyper
              ? "kurulu (HMM veritabanı yoksa yerleşik CRISPR bulucuya düşülür)"
              : "kurulu değil — yerleşik CRISPR bulucu"}{" "}
            · Tür ataması (skani): {durum.skani ? "etkin" : "kapalı"}
          </p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_280px]">
        <DosyaYukle
          onSec={(d) => {
            setDosya(d[0]);
            setSonuc(null);
          }}
          kabul=".fasta,.fa,.fna,.gb,.gbk,.gff,.gff3"
          ipucu="FASTA (.fasta/.fa/.fna), GenBank (.gb/.gbk), GFF (.gff/.gff3)"
        />
        <div className="kart space-y-3 p-4">
          <button
            onClick={analizEt}
            disabled={!dosya || yukleniyor}
            className="w-full rounded-lg bg-marka-600 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
          >
            {yukleniyor ? "Analiz ediliyor…" : "Genomu analiz et"}
          </button>
          <button
            onClick={() => calistir(() => api.genomOrnek(), true)}
            disabled={yukleniyor}
            className="w-full rounded-lg border border-slate-200 py-2 text-sm hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
          >
            Örnek genom ile dene
          </button>
        </div>
      </div>

      {yukleniyor && (
        <IlerlemeCubugu etiket="Dizi okunuyor, CRISPR dizileri ve Cas genleri çıkarılıyor" />
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
            <Istatistik etiket="Kontig" deger={sonuc.kontig_sayisi} />
            <Istatistik
              etiket="Toplam uzunluk"
              deger={`${sonuc.toplam_uzunluk.toLocaleString("tr-TR")} bp`}
            />
            <Istatistik etiket="GC oranı" deger={`%${sonuc.gc_yuzdesi.toFixed(1)}`} />
            <Istatistik etiket="Toplam aralayıcı" deger={sonuc.toplam_aralayici} />
          </div>

          <div className="grid gap-4 md:grid-cols-2">
            <div className="kart p-4">
              <div className="text-xs uppercase tracking-wide text-slate-400">
                En yakın tür / suş
              </div>
              <div className="mt-1 text-lg font-bold">
                {sonuc.tur_eslesmesi
                  ? sonuc.tur_eslesmesi.tur
                  : "Referans kümesi yapılandırılmadı"}
              </div>
              {sonuc.tur_eslesmesi && (
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  ANI %{sonuc.tur_eslesmesi.ani_yuzdesi} · hizalanan kesir %
                  {sonuc.tur_eslesmesi.hizalanan_kesir}
                </div>
              )}
            </div>
            <div className="kart p-4">
              <div className="text-xs uppercase tracking-wide text-slate-400">
                CRISPR-Cas tipi
              </div>
              <div className="mt-1 text-lg font-bold">{sonuc.crispr_cas_tipi}</div>
              <div className="text-sm text-slate-500 dark:text-slate-400">
                {sonuc.cas_genleri.length} Cas gen adayı · yöntem:{" "}
                {sonuc.yontem_crispr}
              </div>
            </div>
          </div>

          <div className="kart overflow-x-auto p-4">
            <h3 className="mb-3 font-semibold">CRISPR dizileri</h3>
            {sonuc.diziler.length === 0 ? (
              <p className="text-sm text-slate-500">CRISPR dizisi bulunamadı.</p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-1.5 pr-3">Kontig</th>
                    <th className="py-1.5 pr-3">Konum</th>
                    <th className="py-1.5 pr-3">Tekrar</th>
                    <th className="py-1.5 pr-3">Aralayıcı</th>
                    <th className="py-1.5 pr-3">Ort. aralayıcı</th>
                    <th className="py-1.5 pr-3">Kimlik</th>
                    <th className="py-1.5">Tekrar konsensüsü</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                  {sonuc.diziler.map((d, i) => (
                    <tr key={i}>
                      <td className="py-1.5 pr-3">{d.kontig}</td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {d.baslangic}–{d.bitis}
                      </td>
                      <td className="py-1.5 pr-3 tabular-nums">{d.tekrar_sayisi}</td>
                      <td className="py-1.5 pr-3 tabular-nums">{d.aralayici_sayisi}</td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        {d.ortalama_aralayici_uzunlugu} bp
                      </td>
                      <td className="py-1.5 pr-3 tabular-nums">
                        %{d.tekrar_kimlik_yuzdesi}
                      </td>
                      <td className="py-1.5 font-mono text-xs">{d.tekrar_konsensus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="grid gap-4 lg:grid-cols-2">
            {sonuc.lokus_haritasi && (
              <figure className="kart overflow-hidden">
                <figcaption className="border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
                  CRISPR lokus haritası
                </figcaption>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={gorselUrl(sonuc.lokus_haritasi)}
                  alt="CRISPR lokus haritası"
                  className="w-full bg-white object-contain p-2 dark:bg-slate-950"
                />
              </figure>
            )}
            {sonuc.genom_haritasi && (
              <figure className="kart overflow-hidden">
                <figcaption className="border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
                  Genom haritası (CRISPR + Cas)
                </figcaption>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img
                  src={gorselUrl(sonuc.genom_haritasi)}
                  alt="Genom haritası"
                  className="w-full bg-white object-contain p-2 dark:bg-slate-950"
                />
              </figure>
            )}
          </div>

          <div className="kart p-4">
            <h3 className="mb-2 font-semibold">Açıklama</h3>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              {sonuc.aciklama}
            </p>
            {sonuc.uyarilar.length > 0 && (
              <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-amber-700 dark:text-amber-300">
                {sonuc.uyarilar.map((u, i) => (
                  <li key={i}>{u}</li>
                ))}
              </ul>
            )}
          </div>

          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-slate-400">İndir:</span>
            <Indir yol={sonuc.pdf_rapor} etiket="PDF" />
            <Indir yol={sonuc.csv_rapor} etiket="CSV (aralayıcılar)" />
            <Indir yol={sonuc.json_rapor} etiket="JSON" />
            <Indir yol={sonuc.html_rapor} etiket="HTML" />
            <Indir yol={sonuc.genom_haritasi} etiket="PNG (harita)" />
          </div>
        </div>
      )}
    </div>
  );
}
