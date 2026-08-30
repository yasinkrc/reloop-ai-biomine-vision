"use client";

import { useState } from "react";
import { DosyaYukle } from "@/components/DosyaYukle";
import { HataKutusu, IlerlemeCubugu, RiskRozet } from "@/components/ortak";
import { SonucGorunumu } from "@/components/SonucGorunumu";
import { api } from "@/lib/api";
import type { TopluSonuc } from "@/lib/tipler";

export default function TopluAnalizSayfa() {
  const [zip, setZip] = useState<File | null>(null);
  const [yukleniyor, setYukleniyor] = useState(false);
  const [sonuc, setSonuc] = useState<TopluSonuc | null>(null);
  const [seciliIdx, setSeciliIdx] = useState(0);
  const [hata, setHata] = useState("");

  async function analizEt() {
    if (!zip) return;
    setYukleniyor(true);
    setHata("");
    try {
      const form = new FormData();
      form.append("dosya", zip);
      const y = await api.topluAnaliz(form);
      setSonuc(y);
      setSeciliIdx(0);
    } catch (e) {
      setHata((e as Error).message);
    } finally {
      setYukleniyor(false);
    }
  }

  async function raporIndir(bicim: "pdf" | "csv" | "json") {
    if (!sonuc) return;
    const idler = sonuc.sonuclar.map((s) => s.id).filter(Boolean);
    const y = await fetch(api.disariAktarUrl, {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ analiz_idleri: idler, bicim }),
    });
    const blob = await y.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `biomine_toplu_${sonuc.numune_id}.${bicim}`;
    a.click();
    URL.revokeObjectURL(url);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Toplu analiz (ZIP)</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          İçinde birden çok görüntü bulunan bir ZIP dosyası yükleyin. Her görüntü ayrı ayrı analiz
          edilir ve toplu rapor üretilir.
        </p>
      </div>

      <DosyaYukle onSec={(d) => { setZip(d[0]); setSonuc(null); }} kabul=".zip" ipucu="Yalnızca .zip" />
      <button
        onClick={analizEt}
        disabled={!zip || yukleniyor}
        className="rounded-lg bg-marka-600 px-5 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
      >
        {yukleniyor ? "Analiz ediliyor…" : "Toplu analiz et"}
      </button>

      {yukleniyor && <IlerlemeCubugu etiket="ZIP açılıyor ve görüntüler sırayla analiz ediliyor" />}
      {hata && <HataKutusu mesaj={hata} />}

      {sonuc && (
        <div className="space-y-4">
          <div className="kart flex flex-wrap items-center justify-between gap-3 p-4">
            <p className="text-sm">{sonuc.ozet_aciklama}</p>
            <div className="flex gap-1">
              {(["pdf", "csv", "json"] as const).map((b) => (
                <button
                  key={b}
                  onClick={() => raporIndir(b)}
                  className="rounded-md border border-slate-200 px-2.5 py-1 text-xs font-medium hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
                >
                  {b.toUpperCase()} indir
                </button>
              ))}
            </div>
          </div>

          <div className="flex flex-wrap gap-2">
            {sonuc.sonuclar.map((s, i) => (
              <button
                key={s.id}
                onClick={() => setSeciliIdx(i)}
                className={`flex items-center gap-2 rounded-lg border px-3 py-1.5 text-xs ${
                  i === seciliIdx
                    ? "border-marka-500 bg-marka-50 dark:bg-marka-900/30"
                    : "border-slate-200 dark:border-slate-700"
                }`}
              >
                #{s.id} · {s.morfoloji.hucre_sayisi} hücre <RiskRozet seviye={s.risk_seviyesi} />
              </button>
            ))}
          </div>

          {sonuc.sonuclar[seciliIdx] && <SonucGorunumu sonuc={sonuc.sonuclar[seciliIdx]} />}
        </div>
      )}
    </div>
  );
}
