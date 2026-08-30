"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { BosDurum, RiskRozet } from "@/components/ortak";
import { api, gorselUrl } from "@/lib/api";
import type { GecmisKaydi } from "@/lib/tipler";

export default function GecmisSayfa() {
  const [kayitlar, setKayitlar] = useState<GecmisKaydi[]>([]);
  const [sadeceRiskli, setSadeceRiskli] = useState(false);
  const [yukleniyor, setYukleniyor] = useState(true);

  function yukle() {
    setYukleniyor(true);
    api.gecmis({ limit: 200, sadece_riskli: sadeceRiskli }).then((k) => {
      setKayitlar(k);
      setYukleniyor(false);
    });
  }

  useEffect(yukle, [sadeceRiskli]);

  async function sil(id: number) {
    if (!confirm(`#${id} numaralı analiz silinsin mi?`)) return;
    await api.gecmisSil(id);
    setKayitlar((k) => k.filter((x) => x.id !== id));
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold">Analiz geçmişi</h1>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={sadeceRiskli} onChange={(e) => setSadeceRiskli(e.target.checked)} />
          Yalnızca riskli sonuçlar
        </label>
      </div>

      {yukleniyor ? (
        <p className="text-sm text-slate-500">Yükleniyor…</p>
      ) : kayitlar.length === 0 ? (
        <BosDurum baslik="Kayıt yok" aciklama="Henüz analiz yapılmadı veya filtreye uyan kayıt yok." />
      ) : (
        <div className="kart overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-xs uppercase text-slate-400 dark:bg-slate-800/50">
              <tr>
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Önizleme</th>
                <th className="px-3 py-2">Tahmin</th>
                <th className="px-3 py-2">Güven</th>
                <th className="px-3 py-2">Hücre</th>
                <th className="px-3 py-2">Risk</th>
                <th className="px-3 py-2">Tarih</th>
                <th className="px-3 py-2"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
              {kayitlar.map((k) => (
                <tr key={k.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50">
                  <td className="px-3 py-2 font-medium">{k.id}</td>
                  <td className="px-3 py-2">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={gorselUrl(k.isaretli_gorsel)} alt="" className="h-12 w-12 rounded object-cover" />
                  </td>
                  <td className="px-3 py-2">
                    <Link href={`/gecmis/${k.id}`} className="text-marka-600 hover:underline">
                      {k.tahmin_sinifi}
                    </Link>
                  </td>
                  <td className="px-3 py-2 tabular-nums">%{k.guven.toFixed(0)}</td>
                  <td className="px-3 py-2 tabular-nums">{k.hucre_sayisi}</td>
                  <td className="px-3 py-2"><RiskRozet seviye={k.risk_seviyesi} /></td>
                  <td className="px-3 py-2 text-xs text-slate-400">
                    {new Date(k.olusturulma).toLocaleString("tr-TR")}
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button onClick={() => sil(k.id)} className="text-xs text-red-500 hover:underline">
                      Sil
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
