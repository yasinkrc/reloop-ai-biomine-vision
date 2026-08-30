"use client";

import { useEffect, useState } from "react";
import { HataKutusu, RiskRozet } from "@/components/ortak";
import { api, gorselUrl } from "@/lib/api";
import type { AnalizSonuc, GecmisKaydi } from "@/lib/tipler";

const FARK_ETIKET: Record<string, string> = {
  hucre_sayisi: "Hücre sayısı",
  kaplama_orani: "Kaplama oranı (%)",
  ort_hucre_alani: "Ort. hücre alanı (px²)",
  ort_uzunluk: "Ort. uzunluk (px)",
  ort_genislik: "Ort. genişlik (px)",
  guven: "Güven (%)",
};

export default function KarsilastirSayfa() {
  const [gecmis, setGecmis] = useState<GecmisKaydi[]>([]);
  const [a, setA] = useState<number | "">("");
  const [b, setB] = useState<number | "">("");
  const [sonuc, setSonuc] = useState<{
    birinci: AnalizSonuc;
    ikinci: AnalizSonuc;
    farklar: Record<string, number>;
    yorum: string;
  } | null>(null);
  const [hata, setHata] = useState("");

  useEffect(() => {
    api.gecmis({ limit: 200 }).then(setGecmis);
  }, []);

  async function karsilastir() {
    if (a === "" || b === "") return;
    setHata("");
    try {
      setSonuc(await api.karsilastir(Number(a), Number(b)));
    } catch (e) {
      setHata((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Numune karşılaştırma</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          İki analiz seçip hücre sayısı, yoğunluk, morfoloji ve sınıflandırma farklarını görün.
        </p>
      </div>

      <div className="flex flex-wrap items-end gap-3">
        {[
          ["1. analiz", a, setA],
          ["2. analiz", b, setB],
        ].map(([etiket, deger, set]) => (
          <label key={etiket as string} className="text-sm">
            <span className="mb-1 block text-slate-500">{etiket as string}</span>
            <select
              value={deger as number | ""}
              onChange={(e) => (set as (v: number | "") => void)(e.target.value ? Number(e.target.value) : "")}
              className="rounded-lg border border-slate-300 bg-white px-3 py-2 dark:border-slate-700 dark:bg-slate-900"
            >
              <option value="">Seçin…</option>
              {gecmis.map((g) => (
                <option key={g.id} value={g.id}>
                  #{g.id} · {g.tahmin_sinifi} · {g.hucre_sayisi} hücre
                </option>
              ))}
            </select>
          </label>
        ))}
        <button
          onClick={karsilastir}
          disabled={a === "" || b === ""}
          className="rounded-lg bg-marka-600 px-5 py-2 font-semibold text-white hover:bg-marka-700 disabled:opacity-40"
        >
          Karşılaştır
        </button>
      </div>

      {hata && <HataKutusu mesaj={hata} />}

      {sonuc && (
        <div className="space-y-4">
          <div className="grid gap-4 sm:grid-cols-2">
            {[sonuc.birinci, sonuc.ikinci].map((s, i) => (
              <div key={i} className="kart p-4">
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="font-semibold">#{s.id} · {i === 0 ? "1. analiz" : "2. analiz"}</h3>
                  <RiskRozet seviye={s.risk_seviyesi} />
                </div>
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={gorselUrl(s.isaretli_gorsel)} alt="" className="aspect-square w-full rounded-lg object-contain" />
                <p className="mt-2 text-sm">
                  {s.tahmin_sinifi} · %{s.guven.toFixed(0)} · {s.morfoloji.hucre_sayisi} hücre
                </p>
              </div>
            ))}
          </div>

          <div className="kart p-4">
            <h3 className="mb-3 font-semibold">Farklar (2. − 1.)</h3>
            <dl className="grid gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              {Object.entries(sonuc.farklar).map(([k, v]) => (
                <div key={k} className="flex justify-between border-b border-slate-100 pb-1 dark:border-slate-800">
                  <dt className="text-slate-500">{FARK_ETIKET[k] ?? k}</dt>
                  <dd className={`font-semibold tabular-nums ${v > 0 ? "text-emerald-600" : v < 0 ? "text-red-600" : ""}`}>
                    {v > 0 ? "+" : ""}
                    {v}
                  </dd>
                </div>
              ))}
            </dl>
          </div>

          <div className="kart p-4 text-sm leading-relaxed text-slate-600 dark:text-slate-300">
            {sonuc.yorum}
          </div>
        </div>
      )}
    </div>
  );
}
