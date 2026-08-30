"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { Saglik } from "@/lib/tipler";
import { useTema } from "./TemaSaglayici";

const BAGLANTILAR = [
  { yol: "/", ad: "Panel" },
  { yol: "/analiz", ad: "Tekli Analiz" },
  { yol: "/toplu", ad: "Toplu Analiz" },
  { yol: "/video", ad: "Video / Zaman Serisi" },
  { yol: "/gecmis", ad: "Geçmiş" },
  { yol: "/karsilastir", ad: "Karşılaştır" },
  { yol: "/ayarlar", ad: "Yönetim" },
];

export function UstBar() {
  const yol = usePathname();
  const { tema, degistir } = useTema();
  const [saglik, setSaglik] = useState<Saglik | null>(null);

  useEffect(() => {
    api.saglik().then(setSaglik).catch(() => setSaglik(null));
  }, []);

  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/85 backdrop-blur dark:border-slate-800 dark:bg-slate-950/85">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-6 gap-y-2 px-4 py-3">
        <Link href="/" className="flex items-center gap-2 font-bold">
          <span className="grid h-8 w-8 place-items-center rounded-lg bg-marka-600 text-white">◎</span>
          <span>BioMine Vision</span>
          <span className="hidden text-xs font-normal text-slate-400 sm:inline">· ReLoop AI</span>
        </Link>

        <nav className="flex flex-1 flex-wrap items-center gap-1 text-sm">
          {BAGLANTILAR.map((b) => {
            const aktif = yol === b.yol;
            return (
              <Link
                key={b.yol}
                href={b.yol}
                className={`rounded-md px-3 py-1.5 transition-colors ${
                  aktif
                    ? "bg-marka-600 text-white"
                    : "text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-slate-800"
                }`}
              >
                {b.ad}
              </Link>
            );
          })}
        </nav>

        <div className="flex items-center gap-3 text-xs">
          {saglik && (
            <span
              className="hidden items-center gap-1.5 rounded-full border border-slate-200 px-2 py-1 text-slate-500 dark:border-slate-700 dark:text-slate-400 md:inline-flex"
              title={`Cihaz: ${saglik.cihaz} · Segmentasyon: ${saglik.segmentasyon_yontemi}`}
            >
              <span
                className={`h-2 w-2 rounded-full ${
                  saglik.durum === "calisiyor" ? "bg-emerald-500" : "bg-red-500"
                }`}
              />
              {saglik.omnipose_hazir ? "Omnipose" : "Klasik seg."} · {saglik.cihaz}
            </span>
          )}
          <button
            onClick={degistir}
            className="rounded-md border border-slate-200 px-2 py-1 hover:bg-slate-100 dark:border-slate-700 dark:hover:bg-slate-800"
            aria-label="Temayı değiştir"
          >
            {tema === "acik" ? "🌙 Koyu" : "☀️ Açık"}
          </button>
        </div>
      </div>
      {saglik && !saglik.siniflandirici_egitildi && (
        <div className="bg-amber-100 px-4 py-1.5 text-center text-xs text-amber-800 dark:bg-amber-900/40 dark:text-amber-200">
          Sınıflandırıcı henüz eğitilmedi — tahminler “Bilinmeyen veya desteklenmeyen bakteri”
          olarak işaretlenir. Eğitmek için: <code>python scripts/model_egit.py</code>
        </div>
      )}
    </header>
  );
}
