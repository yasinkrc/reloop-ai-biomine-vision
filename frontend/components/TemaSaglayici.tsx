"use client";

import { createContext, useCallback, useContext, useEffect, useState } from "react";

type Tema = "acik" | "koyu";
const TemaBaglam = createContext<{ tema: Tema; degistir: () => void }>({
  tema: "acik",
  degistir: () => {},
});

export function TemaSaglayici({ children }: { children: React.ReactNode }) {
  const [tema, setTema] = useState<Tema>("acik");

  useEffect(() => {
    const kayitli = (localStorage.getItem("biomine-tema") as Tema | null) ?? null;
    const sistem = window.matchMedia("(prefers-color-scheme: dark)").matches ? "koyu" : "acik";
    const secilen = kayitli ?? sistem;
    setTema(secilen);
    document.documentElement.classList.toggle("dark", secilen === "koyu");
  }, []);

  const degistir = useCallback(() => {
    setTema((onceki) => {
      const yeni = onceki === "acik" ? "koyu" : "acik";
      localStorage.setItem("biomine-tema", yeni);
      document.documentElement.classList.toggle("dark", yeni === "koyu");
      return yeni;
    });
  }, []);

  return <TemaBaglam.Provider value={{ tema, degistir }}>{children}</TemaBaglam.Provider>;
}

export const useTema = () => useContext(TemaBaglam);
