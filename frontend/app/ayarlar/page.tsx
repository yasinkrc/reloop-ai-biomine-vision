"use client";

import { useEffect, useState } from "react";
import { HataKutusu } from "@/components/ortak";
import { api } from "@/lib/api";
import type { AyarKaydi } from "@/lib/tipler";

export default function YonetimSayfa() {
  const [ayarlar, setAyarlar] = useState<AyarKaydi[]>([]);
  const [siniflar, setSiniflar] = useState<{ anahtar: string; etiket: string }[]>([]);
  const [not, setNot] = useState("");
  const [taslak, setTaslak] = useState<Record<string, number>>({});
  const [durum, setDurum] = useState("");
  const [hata, setHata] = useState("");

  useEffect(() => {
    api.ayarlar().then((a) => {
      setAyarlar(a);
      setTaslak(Object.fromEntries(a.map((x) => [x.anahtar, x.deger])));
    }).catch((e) => setHata(String(e)));
    api.desteklenenSiniflar().then((s) => {
      setSiniflar(s.siniflar);
      setNot(s.not);
    });
  }, []);

  async function kaydet(anahtar: string) {
    setDurum("");
    setHata("");
    try {
      const guncel = await api.ayarGuncelle(anahtar, taslak[anahtar]);
      setAyarlar((a) => a.map((x) => (x.anahtar === anahtar ? guncel : x)));
      setDurum(`"${anahtar}" güncellendi (${guncel.deger}).`);
    } catch (e) {
      setHata((e as Error).message);
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-xl font-bold">Yönetim — eşik değerleri</h1>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          Kural motorunun kullandığı tüm eşikler buradan değiştirilebilir. Değişiklikler
          veritabanına yazılır ve hemen etkili olur.
        </p>
      </div>

      {hata && <HataKutusu mesaj={hata} />}
      {durum && <p className="text-sm text-emerald-600">{durum}</p>}

      <div className="kart divide-y divide-slate-100 dark:divide-slate-800">
        {ayarlar.map((a) => (
          <div key={a.anahtar} className="flex flex-wrap items-center gap-3 p-4">
            <div className="min-w-[220px] flex-1">
              <div className="font-mono text-sm font-semibold">{a.anahtar}</div>
              <div className="text-xs text-slate-500 dark:text-slate-400">{a.aciklama}</div>
            </div>
            <input
              type="number"
              step="0.1"
              value={taslak[a.anahtar] ?? a.deger}
              onChange={(e) => setTaslak((t) => ({ ...t, [a.anahtar]: Number(e.target.value) }))}
              className="w-28 rounded-lg border border-slate-300 bg-white px-2 py-1 text-sm dark:border-slate-700 dark:bg-slate-900"
            />
            <button
              onClick={() => kaydet(a.anahtar)}
              disabled={taslak[a.anahtar] === a.deger}
              className="rounded-md bg-marka-600 px-3 py-1 text-sm font-medium text-white hover:bg-marka-700 disabled:opacity-40"
            >
              Kaydet
            </button>
          </div>
        ))}
        {ayarlar.length === 0 && !hata && <p className="p-4 text-sm text-slate-500">Yükleniyor…</p>}
      </div>

      <div className="kart p-4">
        <h2 className="mb-2 font-semibold">Modelin desteklediği sınıflar</h2>
        <p className="mb-3 text-xs text-slate-500 dark:text-slate-400">{not}</p>
        <div className="flex flex-wrap gap-2">
          {siniflar.map((s) => (
            <span key={s.anahtar} className="rounded-full bg-slate-100 px-3 py-1 text-xs dark:bg-slate-800">
              {s.etiket}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
