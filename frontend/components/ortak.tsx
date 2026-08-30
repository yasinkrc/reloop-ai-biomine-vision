"use client";

import type { RiskSeviyesi } from "@/lib/tipler";

export function RiskRozet({ seviye }: { seviye: RiskSeviyesi }) {
  const harita: Record<RiskSeviyesi, { etiket: string; sinif: string }> = {
    normal: { etiket: "Normal", sinif: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/50 dark:text-emerald-200" },
    dikkat: { etiket: "Dikkat", sinif: "bg-amber-100 text-amber-800 dark:bg-amber-900/50 dark:text-amber-200" },
    kritik: { etiket: "Kritik", sinif: "bg-red-100 text-red-800 dark:bg-red-900/50 dark:text-red-200" },
  };
  const s = harita[seviye] ?? harita.normal;
  return (
    <span className={`rozet ${s.sinif}`} role="status">
      <span className="h-1.5 w-1.5 rounded-full bg-current" /> {s.etiket}
    </span>
  );
}

export function BosDurum({ baslik, aciklama, ikon = "🧫" }: { baslik: string; aciklama?: string; ikon?: string }) {
  return (
    <div className="kart flex flex-col items-center gap-2 p-10 text-center">
      <div className="text-4xl">{ikon}</div>
      <p className="font-semibold">{baslik}</p>
      {aciklama && <p className="max-w-md text-sm text-slate-500 dark:text-slate-400">{aciklama}</p>}
    </div>
  );
}

export function HataKutusu({ mesaj }: { mesaj: string }) {
  return (
    <div
      role="alert"
      className="rounded-lg border border-red-300 bg-red-50 px-4 py-3 text-sm text-red-800 dark:border-red-800 dark:bg-red-950/50 dark:text-red-200"
    >
      <strong>Hata:</strong> {mesaj}
    </div>
  );
}

export function IlerlemeCubugu({ etiket, belirsiz = true, oran }: { etiket: string; belirsiz?: boolean; oran?: number }) {
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-slate-500 dark:text-slate-400">
        <span>{etiket}</span>
        {!belirsiz && oran != null && <span>%{Math.round(oran)}</span>}
      </div>
      <div className="h-2.5 w-full overflow-hidden rounded-full bg-slate-200 dark:bg-slate-800">
        <div
          className={`h-full rounded-full bg-marka-600 ${belirsiz ? "ilerleme-serit w-2/3" : ""}`}
          style={belirsiz ? undefined : { width: `${Math.min(100, Math.max(0, oran ?? 0))}%` }}
        />
      </div>
    </div>
  );
}

export function Istatistik({ etiket, deger, alt }: { etiket: string; deger: React.ReactNode; alt?: string }) {
  return (
    <div className="kart p-4">
      <div className="text-xs uppercase tracking-wide text-slate-400">{etiket}</div>
      <div className="mt-1 text-2xl font-bold">{deger}</div>
      {alt && <div className="text-xs text-slate-500 dark:text-slate-400">{alt}</div>}
    </div>
  );
}
