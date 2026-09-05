"use client";

import { useEffect, useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu, Istatistik } from "@/components/ortak";
import { api, gorselUrl } from "@/lib/api";
import type { GenomSonuc, GorsellestirmeAyari } from "@/lib/tipler";

const cn =
  "rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800";

function Indir({ yol, etiket }: { yol: string | null; etiket: string }) {
  if (!yol) return null;
  return (
    <a href={gorselUrl(yol)} download className={cn}>
      {etiket}
    </a>
  );
}

function GorselKart({
  baslik,
  yol,
  htmlYol,
}: {
  baslik: string;
  yol: string;
  htmlYol?: string | null;
}) {
  return (
    <figure className="kart overflow-hidden">
      <figcaption className="flex items-center justify-between border-b border-slate-100 px-3 py-2 text-sm font-medium dark:border-slate-800">
        <span>{baslik}</span>
        {htmlYol && (
          <a
            href={gorselUrl(htmlYol)}
            target="_blank"
            rel="noreferrer"
            className="text-xs text-marka-600 hover:underline"
          >
            Etkileşimli HTML →
          </a>
        )}
      </figcaption>
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={gorselUrl(yol)}
        alt={baslik}
        className="w-full bg-white object-contain p-2 dark:bg-slate-950"
      />
    </figure>
  );
}

const TIP = [
  ["otomatik", "Otomatik"],
  ["karsilastirmali", "Karşılaştırmalı doğrusal (sinteni)"],
  ["tekli", "Tekli doğrusal"],
  ["dairesel", "Dairesel (Circos)"],
  ["hepsi", "Hepsi"],
];
const STIL = ["bigarrow", "arrow", "box", "bigbox", "rbox", "bigrbox"];
const ETIKET = [
  ["yok", "Yok"],
  ["ust", "Sadece üst şerit"],
  ["tumu", "Tüm şeritler"],
];
const LINK = [
  ["gri-kirmizi", "Gri → Kırmızı"],
  ["turuncu-yesil", "Turuncu → Yeşil"],
  ["mavi-kirmizi", "Mavi → Kırmızı"],
];

export default function CrisprSayfa() {
  const [dosyalar, setDosyalar] = useState<File[]>([]);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<GenomSonuc | null>(null);
  const [ornekMi, setOrnekMi] = useState(false);
  const [hata, setHata] = useState("");
  const [durum, setDurum] = useState<Record<string, boolean | number> | null>(null);

  const [ayar, setAyar] = useState<GorsellestirmeAyari>({
    tip: "otomatik",
    gen_stili: "bigarrow",
    etiket: "ust",
    link_renk: "gri-kirmizi",
    min_kimlik: 30,
  });

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
    if (dosyalar.length === 0) return;
    const form = new FormData();
    dosyalar.forEach((d) => form.append("dosyalar", d));
    form.append("tip", ayar.tip);
    form.append("gen_stili", ayar.gen_stili);
    form.append("etiket", ayar.etiket);
    form.append("link_renk", ayar.link_renk);
    form.append("min_kimlik", String(ayar.min_kimlik));
    calistir(() => api.genomAnaliz(form), false);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Bakteriyel CRISPR-Cas Analizi</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Bir veya <strong>birden çok</strong> FASTA / GenBank / GFF bakteriyel DNA
          dosyası yükleyin. pyGenomeViz ile <strong>karşılaştırmalı doğrusal sinteni</strong>{" "}
          ve <strong>tekli doğrusal</strong>, pyCirclize ile <strong>dairesel (Circos)</strong>{" "}
          genom haritaları üretilir. Tek genomda ayrıca: en yakın tür/suş (ANI),
          CRISPR dizileri + aralayıcı sayıları, Cas gen adayları, CRISPR-Cas tipi ve
          CRISPR lokus haritası. Çıktı PNG, PDF, HTML, CSV, JSON.
        </p>
        {durum && (
          <p className="mt-1 text-xs text-slate-400">
            Sinteni (MMseqs2/MUMmer): {durum.mmseqs || durum.mummer ? "etkin" : "kapalı"} ·
            Dairesel (pyCirclize): {durum.pycirclize ? "etkin" : "kapalı"} ·
            CRISPRCasTyper: {durum.cctyper ? "kurulu" : "kapalı"} ·
            Tür ataması (skani): {durum.skani ? "etkin" : "kapalı"}
          </p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        <div className="space-y-4">
          <DosyaYukle
            onSec={(d) => {
              setDosyalar(d);
              setSonuc(null);
            }}
            kabul=".fasta,.fa,.fna,.gb,.gbk,.gbff,.gff,.gff3"
            coklu
            ipucu="FASTA / GenBank / GFF · birden çok dosya seçebilirsiniz (en fazla 8)"
          />
          <div className="flex flex-wrap gap-2">
            <span className="self-center text-xs text-slate-400">Örneklerle dene:</span>
            <button onClick={() => calistir(() => api.genomOrnek(ayar), true)} disabled={yukleniyor} className={cn}>
              4 faj karşılaştırması
            </button>
            <button onClick={() => calistir(() => api.genomOrnekBakteri(ayar), true)} disabled={yukleniyor} className={cn}>
              Bakteri genomu (gerçek, açıklamalı)
            </button>
            <button onClick={() => calistir(() => api.genomOrnekCrispr(ayar), true)} disabled={yukleniyor} className={cn}>
              CRISPR&apos;lı genom (sentetik)
            </button>
          </div>
        </div>

        {/* Görselleştirme ayarları — pyGenomeViz/pyCirclize denetim paneli */}
        <div className="kart space-y-3 p-4">
          <h2 className="font-semibold">Görselleştirme ayarları</h2>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-500">Harita tipi</span>
            <select
              value={ayar.tip}
              onChange={(e) => setAyar({ ...ayar, tip: e.target.value })}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {TIP.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-500">Gen oku stili</span>
            <select
              value={ayar.gen_stili}
              onChange={(e) => setAyar({ ...ayar, gen_stili: e.target.value })}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {STIL.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-500">Gen adı etiketi</span>
            <select
              value={ayar.etiket}
              onChange={(e) => setAyar({ ...ayar, etiket: e.target.value })}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {ETIKET.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 block text-slate-500">Sinteni bağlantı rengi</span>
            <select
              value={ayar.link_renk}
              onChange={(e) => setAyar({ ...ayar, link_renk: e.target.value })}
              className="w-full rounded-lg border border-slate-300 bg-white px-2 py-1.5 text-sm dark:border-slate-700 dark:bg-slate-900"
            >
              {LINK.map(([v, l]) => (
                <option key={v} value={v}>{l}</option>
              ))}
            </select>
          </label>

          <label className="block text-sm">
            <span className="mb-1 flex justify-between text-slate-500">
              <span>En düşük bağlantı kimliği</span>
              <strong>%{ayar.min_kimlik}</strong>
            </span>
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={ayar.min_kimlik}
              onChange={(e) => setAyar({ ...ayar, min_kimlik: Number(e.target.value) })}
              className="w-full"
            />
          </label>

          <button
            onClick={analizEt}
            disabled={dosyalar.length === 0 || yukleniyor}
            className="w-full rounded-lg bg-marka-600 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
          >
            {yukleniyor
              ? "Analiz ediliyor…"
              : dosyalar.length > 1
                ? `${dosyalar.length} genomu analiz et`
                : "Genomu analiz et"}
          </button>
        </div>
      </div>

      {yukleniyor && (
        <IlerlemeCubugu etiket="Diziler okunuyor, CRISPR + Cas çıkarılıyor, haritalar çiziliyor" />
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
            <Istatistik etiket="Genom" deger={sonuc.genom_sayisi} />
            <Istatistik
              etiket="Toplam uzunluk"
              deger={`${sonuc.toplam_uzunluk.toLocaleString("tr-TR")} bp`}
            />
            <Istatistik
              etiket={sonuc.karsilastirmali ? "Sinteni bağlantısı" : "GC oranı"}
              deger={
                sonuc.karsilastirmali
                  ? `${sonuc.hizalama_sayisi} (${sonuc.hizalama_yontemi})`
                  : `%${sonuc.gc_yuzdesi.toFixed(1)}`
              }
            />
            <Istatistik etiket="Toplam aralayıcı" deger={sonuc.toplam_aralayici} />
          </div>

          {/* Karşılaştırmalı doğrusal sinteni haritası */}
          {sonuc.karsilastirmali && sonuc.genom_haritasi && (
            <GorselKart
              baslik="Karşılaştırmalı genom / sinteni haritası (pyGenomeViz)"
              yol={sonuc.genom_haritasi}
              htmlYol={sonuc.karsilastirma_html}
            />
          )}

          {/* Tekli doğrusal harita */}
          {sonuc.dogrusal_harita && (
            <GorselKart
              baslik="Tekli doğrusal genom haritası — genler + CRISPR/Cas (pyGenomeViz)"
              yol={sonuc.dogrusal_harita}
            />
          )}

          {/* Dairesel (Circos) haritalar */}
          {sonuc.dairesel_haritalar.length > 0 && (
            <div className="grid gap-4 md:grid-cols-2">
              {sonuc.dairesel_haritalar.map((h) => (
                <GorselKart
                  key={h.png}
                  baslik={`Dairesel harita — ${h.ad} (pyCirclize: CDS ± GC içeriği · GC eğriliği)`}
                  yol={h.png}
                />
              ))}
            </div>
          )}

          {/* Genom tablosu */}
          <div className="kart overflow-x-auto p-4">
            <h3 className="mb-3 font-semibold">Genomlar</h3>
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase text-slate-400">
                <tr>
                  <th className="py-1.5 pr-3">Ad</th>
                  <th className="py-1.5 pr-3">Uzunluk</th>
                  <th className="py-1.5 pr-3">GC</th>
                  <th className="py-1.5 pr-3">Gen</th>
                  <th className="py-1.5 pr-3">CRISPR</th>
                  <th className="py-1.5 pr-3">Aralayıcı</th>
                  <th className="py-1.5 pr-3">Cas adayı</th>
                  <th className="py-1.5">En yakın tür</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                {sonuc.genomlar.map((g) => (
                  <tr key={g.ad}>
                    <td className="py-1.5 pr-3 font-medium">{g.ad}</td>
                    <td className="py-1.5 pr-3 tabular-nums">
                      {g.toplam_uzunluk.toLocaleString("tr-TR")} bp
                    </td>
                    <td className="py-1.5 pr-3 tabular-nums">%{g.gc_yuzdesi.toFixed(1)}</td>
                    <td className="py-1.5 pr-3 tabular-nums">
                      {g.gen_sayisi} <span className="text-slate-400">({g.gen_kaynagi})</span>
                    </td>
                    <td className="py-1.5 pr-3 tabular-nums">{g.crispr_dizisi}</td>
                    <td className="py-1.5 pr-3 tabular-nums">{g.toplam_aralayici}</td>
                    <td className="py-1.5 pr-3 tabular-nums">{g.cas_gen_adayi}</td>
                    <td className="py-1.5">
                      {g.tur_eslesmesi
                        ? `${g.tur_eslesmesi.tur} (%${g.tur_eslesmesi.ani_yuzdesi})`
                        : "—"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {!sonuc.karsilastirmali && (
            <div className="grid gap-4 md:grid-cols-2">
              <div className="kart p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">
                  CRISPR-Cas tipi
                </div>
                <div className="mt-1 text-lg font-bold">{sonuc.crispr_cas_tipi}</div>
                <div className="text-sm text-slate-500 dark:text-slate-400">
                  {sonuc.cas_genleri.length} Cas gen adayı · yöntem: {sonuc.yontem_crispr}
                </div>
              </div>
              <div className="kart p-4">
                <div className="text-xs uppercase tracking-wide text-slate-400">
                  En yakın tür / suş
                </div>
                <div className="mt-1 text-lg font-bold">
                  {sonuc.tur_eslesmesi
                    ? `${sonuc.tur_eslesmesi.tur}`
                    : "Referans kümesi yapılandırılmadı"}
                </div>
                {sonuc.tur_eslesmesi && (
                  <div className="text-sm text-slate-500 dark:text-slate-400">
                    ANI %{sonuc.tur_eslesmesi.ani_yuzdesi} · hizalanan kesir %
                    {sonuc.tur_eslesmesi.hizalanan_kesir}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* CRISPR dizileri tablosu */}
          <div className="kart overflow-x-auto p-4">
            <h3 className="mb-3 font-semibold">CRISPR dizileri ({sonuc.diziler.length})</h3>
            {sonuc.diziler.length === 0 ? (
              <p className="text-sm text-slate-500">
                Bu genom(lar)da CRISPR dizisi bulunamadı. (Fajlarda CRISPR beklenmez;
                bakteriyel genom deneyin.)
              </p>
            ) : (
              <table className="w-full text-sm">
                <thead className="text-left text-xs uppercase text-slate-400">
                  <tr>
                    <th className="py-1.5 pr-3">Kontig</th>
                    <th className="py-1.5 pr-3">Konum</th>
                    <th className="py-1.5 pr-3">Tekrar</th>
                    <th className="py-1.5 pr-3">Aralayıcı</th>
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
                        %{d.tekrar_kimlik_yuzdesi}
                      </td>
                      <td className="py-1.5 font-mono text-xs">{d.tekrar_konsensus}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          {sonuc.lokus_haritasi && (
            <GorselKart
              baslik="CRISPR lokus haritası (tekrarlar + numaralı aralayıcılar)"
              yol={sonuc.lokus_haritasi}
            />
          )}

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
            <Indir yol={sonuc.html_rapor} etiket="HTML rapor" />
            <Indir yol={sonuc.karsilastirma_html} etiket="Etkileşimli sinteni (HTML)" />
            <Indir yol={sonuc.genom_haritasi} etiket="PNG (ana harita)" />
            <Indir yol={sonuc.dogrusal_harita} etiket="PNG (doğrusal)" />
            {sonuc.dairesel_haritalar[0] && (
              <Indir yol={sonuc.dairesel_haritalar[0].png} etiket="PNG (dairesel)" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}
