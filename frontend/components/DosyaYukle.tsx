"use client";

import { useCallback, useRef, useState } from "react";

interface Props {
  onSec: (dosyalar: File[]) => void;
  kabul?: string;
  coklu?: boolean;
  ipucu?: string;
}

export function DosyaYukle({ onSec, kabul = "image/*", coklu = false, ipucu }: Props) {
  const [aktif, setAktif] = useState(false);
  const [adlar, setAdlar] = useState<string[]>([]);
  const girisRef = useRef<HTMLInputElement>(null);

  const isle = useCallback(
    (liste: FileList | null) => {
      if (!liste || liste.length === 0) return;
      const dosyalar = Array.from(liste).slice(0, coklu ? undefined : 1);
      setAdlar(dosyalar.map((d) => d.name));
      onSec(dosyalar);
    },
    [coklu, onSec],
  );

  return (
    <div
      className={`birak-alani ${aktif ? "aktif" : "border-slate-300 dark:border-slate-700"} cursor-pointer p-8 text-center`}
      onDragOver={(e) => {
        e.preventDefault();
        setAktif(true);
      }}
      onDragLeave={() => setAktif(false)}
      onDrop={(e) => {
        e.preventDefault();
        setAktif(false);
        isle(e.dataTransfer.files);
      }}
      onClick={() => girisRef.current?.click()}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") girisRef.current?.click();
      }}
      role="button"
      tabIndex={0}
      aria-label="Dosya yükle"
    >
      <input
        ref={girisRef}
        type="file"
        accept={kabul}
        multiple={coklu}
        className="hidden"
        onChange={(e) => isle(e.target.files)}
      />
      <div className="text-3xl">⬆️</div>
      <p className="mt-2 font-medium">
        Dosyayı buraya sürükleyip bırakın <span className="text-slate-400">veya tıklayın</span>
      </p>
      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
        {ipucu ?? "JPG, PNG, TIFF"}
      </p>
      {adlar.length > 0 && (
        <ul className="mx-auto mt-3 max-w-md space-y-1 text-left text-xs text-slate-600 dark:text-slate-300">
          {adlar.slice(0, 6).map((a) => (
            <li key={a} className="truncate rounded bg-slate-100 px-2 py-1 dark:bg-slate-800">
              📄 {a}
            </li>
          ))}
          {adlar.length > 6 && <li className="text-slate-400">+{adlar.length - 6} dosya daha</li>}
        </ul>
      )}
    </div>
  );
}
