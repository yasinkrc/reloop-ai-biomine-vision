"use client";

import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts";
import type { AnalizSonuc, ZamanNoktasi } from "@/lib/tipler";

export function ZamanSerisiGrafik({ veri }: { veri: ZamanNoktasi[] }) {
  const nokta = veri.map((z) => ({
    zaman: z.zaman_sn,
    "Hücre sayısı": z.hucre_sayisi,
    "Kaplama %": Number(z.kaplama_orani.toFixed(1)),
  }));
  return (
    <div className="kart p-4">
      <h3 className="mb-3 font-semibold">Zamanla hücre sayısı ve yoğunluk</h3>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={nokta} margin={{ top: 5, right: 20, bottom: 5, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
          <XAxis dataKey="zaman" unit="s" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="sol" tick={{ fontSize: 12 }} />
          <YAxis yAxisId="sag" orientation="right" tick={{ fontSize: 12 }} />
          <Tooltip contentStyle={{ fontSize: 12 }} />
          <Legend />
          <Line yAxisId="sol" type="monotone" dataKey="Hücre sayısı" stroke="#0891b2" strokeWidth={2} dot />
          <Line yAxisId="sag" type="monotone" dataKey="Kaplama %" stroke="#d97706" strokeWidth={2} dot />
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}

export function HucreDagilimGrafik({ sonuc }: { sonuc: AnalizSonuc }) {
  const nokta = sonuc.hucreler.map((h) => ({
    uzunluk: Number(h.uzunluk.toFixed(1)),
    genislik: Number(h.genislik.toFixed(1)),
    alan: Number(h.alan.toFixed(0)),
    morfoloji: h.morfoloji,
  }));
  const gruplar = ["cubuk", "kuresel", "filamentli"] as const;
  const renk: Record<string, string> = { cubuk: "#0891b2", kuresel: "#7c3aed", filamentli: "#d97706" };
  return (
    <div className="kart p-4">
      <h3 className="mb-3 font-semibold">Hücre boyut dağılımı (uzunluk × genişlik)</h3>
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 5, right: 20, bottom: 10, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#94a3b833" />
          <XAxis type="number" dataKey="uzunluk" name="Uzunluk" unit="px" tick={{ fontSize: 12 }} />
          <YAxis type="number" dataKey="genislik" name="Genişlik" unit="px" tick={{ fontSize: 12 }} />
          <ZAxis type="number" dataKey="alan" range={[20, 200]} name="Alan" />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} contentStyle={{ fontSize: 12 }} />
          <Legend />
          {gruplar.map((g) => (
            <Scatter key={g} name={g} data={nokta.filter((n) => n.morfoloji === g)} fill={renk[g]} />
          ))}
        </ScatterChart>
      </ResponsiveContainer>
    </div>
  );
}
