"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HataKutusu } from "@/components/ortak";
import { HucreDagilimGrafik } from "@/components/Grafikler";
import { SonucGorunumu } from "@/components/SonucGorunumu";
import { api } from "@/lib/api";
import type { AnalizSonuc } from "@/lib/tipler";

export default function GecmisDetay({ params }: { params: { id: string } }) {
  const [sonuc, setSonuc] = useState<AnalizSonuc | null>(null);
  const [hata, setHata] = useState("");

  useEffect(() => {
    api.gecmisGetir(Number(params.id)).then(setSonuc).catch((e) => setHata(String(e)));
  }, [params.id]);

  return (
    <div className="space-y-4">
      <Link href="/gecmis" className="text-sm text-marka-600 hover:underline">
        ← Geçmişe dön
      </Link>
      <h1 className="text-xl font-bold">Analiz #{params.id}</h1>
      {hata && <HataKutusu mesaj={hata} />}
      {sonuc && (
        <>
          <SonucGorunumu sonuc={sonuc} />
          {sonuc.hucreler.length > 0 && <HucreDagilimGrafik sonuc={sonuc} />}
        </>
      )}
    </div>
  );
}
