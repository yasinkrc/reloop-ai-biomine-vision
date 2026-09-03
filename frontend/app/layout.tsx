import type { Metadata } from "next";
import "./globals.css";
import { TemaSaglayici } from "@/components/TemaSaglayici";
import { UstBar } from "@/components/UstBar";

export const metadata: Metadata = {
  title: "BioMine Vision — Biyoliç Mikroskop Görüntü Analizi",
  description:
    "ReLoop AI — Biyoliç ve mikrobiyoloji mikroskop görüntülerini yapay zeka ile analiz eden uçtan uca platform.",
};

export default function KokDuzen({ children }: { children: React.ReactNode }) {
  return (
    <html lang="tr" suppressHydrationWarning>
      <body>
        <TemaSaglayici>
          <UstBar />
          <main className="mx-auto max-w-7xl px-4 py-6">{children}</main>
          <footer className="mx-auto max-w-7xl px-4 pb-10 pt-4 text-center text-xs text-slate-400">
            BioMine Vision · ReLoop AI · Yalnızca araştırma ve eğitim amaçlıdır;
            klinik tanı veya laboratuvar doğrulamasının yerine geçmez.
          </footer>
        </TemaSaglayici>
      </body>
    </html>
  );
}
