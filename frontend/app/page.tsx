"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { Istatistik } from "@/components/ortak";
import { RiskRozet } from "@/components/ortak";
import { api } from "@/lib/api";
import type { GecmisKaydi, Saglik } from "@/lib/tipler";

export default function Panel() {
  const [saglik, setSaglik] = useState<Saglik | null>(null);
  const [gecmis, setGecmis] = useState<GecmisKaydi[]>([]);
  const [hata, setHata] = useState("");

  useEffect(() => {
    api.saglik().then(setSaglik).catch((e) => setHata(String(e)));
    api.gecmis({ limit: 100 }).then(setGecmis).catch(() => {});
  }, []);

  const toplam = gecmis.length;
  const riskli = gecmis.filter((g) => g.risk_seviyesi !== "normal").length;
  const ortHucre = toplam ? Math.round(gecmis.reduce((t, g) => t + g.hucre_sayisi, 0) / toplam) : 0;
  const desteklenmeyen = gecmis.filter((g) => g.desteklenmiyor).length;

  return (
    <div className="space-y-8">
      <section className="rounded-2xl bg-gradient-to-br from-marka-600 to-marka-900 p-8 text-white">
        <h1 className="text-2xl font-bold sm:text-3xl">BioMine Vision</h1>
        <p className="mt-2 max-w-2xl text-marka-50">
          Biyoliç ve mikrobiyoloji mikroskop görüntülerini yapay zeka ile inceleyin: bakterileri
          tespit edin, renkli işaretleyin, sayın, morfolojilerini ölçün, sınıfını tahmin edin ve
          sonuçları anlaşılır Türkçe uyarılara dönüştürün.
        </p>
        <div className="mt-5 flex flex-wrap gap-3">
          <Link href="/analiz" className="rounded-lg bg-white px-4 py-2 font-semibold text-marka-700 hover:bg-marka-50">
            Tekli görüntü analizi
          </Link>
          <Link href="/toplu" className="rounded-lg border border-white/40 px-4 py-2 font-semibold hover:bg-white/10">
            Toplu (ZIP) analiz
          </Link>
          <Link href="/video" className="rounded-lg border border-white/40 px-4 py-2 font-semibold hover:bg-white/10">
            Video / zaman serisi
          </Link>
        </div>
      </section>

      <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <Istatistik etiket="Toplam analiz" deger={toplam} />
        <Istatistik etiket="Riskli sonuç" deger={riskli} alt={`${toplam ? Math.round((riskli / toplam) * 100) : 0}%`} />
        <Istatistik etiket="Ortalama hücre / görüntü" deger={ortHucre} />
        <Istatistik etiket="Desteklenmeyen / bilinmeyen" deger={desteklenmeyen} />
      </section>

      <section className="grid gap-6 lg:grid-cols-3">
        <div className="kart p-4 lg:col-span-2">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="font-semibold">Son analizler</h2>
            <Link href="/gecmis" className="text-sm text-marka-600 hover:underline">
              Tümünü gör →
            </Link>
          </div>
          {gecmis.length === 0 ? (
            <p className="py-8 text-center text-sm text-slate-500">
              Henüz analiz yok. <Link href="/analiz" className="text-marka-600 hover:underline">İlk görüntünü yükle</Link>.
            </p>
          ) : (
            <ul className="divide-y divide-slate-100 dark:divide-slate-800">
              {gecmis.slice(0, 8).map((g) => (
                <li key={g.id} className="flex items-center justify-between gap-3 py-2 text-sm">
                  <Link href={`/gecmis/${g.id}`} className="flex-1 truncate hover:underline">
                    #{g.id} · {g.tahmin_sinifi}
                  </Link>
                  <span className="tabular-nums text-slate-400">%{g.guven.toFixed(0)}</span>
                  <span className="tabular-nums text-slate-400">{g.hucre_sayisi} hücre</span>
                  <RiskRozet seviye={g.risk_seviyesi} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="kart p-4">
          <h2 className="mb-3 font-semibold">Sistem durumu</h2>
          {hata && <p className="text-sm text-red-600">API'ye ulaşılamadı: {hata}</p>}
          {saglik && (
            <dl className="space-y-2 text-sm">
              <div className="flex justify-between"><dt className="text-slate-500">Durum</dt><dd className="font-medium">{saglik.durum}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Sürüm</dt><dd className="font-medium">{saglik.surum}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Cihaz</dt><dd className="font-medium">{saglik.cihaz}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Segmentasyon</dt><dd className="font-medium">{saglik.segmentasyon_yontemi}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Omnipose</dt><dd className="font-medium">{saglik.omnipose_hazir ? "hazır" : "yok (klasik)"}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Sınıflandırıcı</dt><dd className="font-medium">{saglik.siniflandirici_egitildi ? "eğitildi" : "eğitilmedi (demo)"}</dd></div>
              <div className="flex justify-between"><dt className="text-slate-500">Desteklenen sınıf</dt><dd className="font-medium">{saglik.desteklenen_sinif_sayisi}</dd></div>
            </dl>
          )}
        </div>
      </section>
    </div>
  );
}
