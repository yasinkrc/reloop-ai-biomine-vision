#!/usr/bin/env python3
"""Örnek bakteriyel genom (gömülü CRISPR dizili) + skani referans kümesi üretir.

Gerçek etiketli bakteriyel genom paylaşımı büyük dosyalar gerektirir; bu betik
CRISPR-Cas analiz akışını uçtan uca denemek için:
  * ~60 kb sentetik bir kontig,
  * içine gömülü kanonik bir CRISPR dizisi (28 bp tekrar + 32 bp aralayıcılar),
  * "cas benzeri" birkaç uzun ORF,
  * skani için 3 referans genom (yakın / orta / uzak benzerlik)
üretir.

Kullanım:  python scripts/ornek_genom_uret.py
"""
from __future__ import annotations

import random
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "ornek_veri" / "genom"
REF = CIKTI / "referans"

# E. coli K-12 CRISPR2 tekrar konsensüsü (28 bp) — kamuya açık, kanonik dizi
TEKRAR = "GTGTTCCCCGCGCCAGCGGGGATAAACCG"
BAZ = "ACGT"


def rastgele_dizi(n: int, rng: random.Random, gc: float = 0.51) -> str:
    olas = [(1 - gc) / 2, gc / 2, gc / 2, (1 - gc) / 2]  # A C G T
    return "".join(rng.choices(BAZ, weights=olas, k=n))


def orf(rng: random.Random, uzunluk: int) -> str:
    """Basit ORF: ATG ... (kodon çoğunluğu) ... TAA."""
    govde = rastgele_dizi(uzunluk - 6, rng)
    # stop kodonlarını gövdeden azalt
    for stop in ("TAA", "TAG", "TGA"):
        govde = govde.replace(stop, "TAC")
    return "ATG" + govde + "TAA"


def crispr_dizi(rng: random.Random, aralayici_sayisi: int = 18) -> str:
    parcalar = []
    for i in range(aralayici_sayisi):
        parcalar.append(TEKRAR)
        parcalar.append(rastgele_dizi(rng.randint(30, 34), rng))  # aralayıcı
    parcalar.append(TEKRAR)  # kapanış tekrarı
    return "".join(parcalar)


def genom_kur(rng: random.Random) -> str:
    p = [rastgele_dizi(6000, rng)]
    # birkaç cas-benzeri uzun ORF (CRISPR'a yakın)
    for _ in range(4):
        p.append(orf(rng, rng.randint(900, 2400)))
        p.append(rastgele_dizi(rng.randint(200, 600), rng))
    p.append(crispr_dizi(rng))
    p.append(rastgele_dizi(4000, rng))
    for _ in range(3):
        p.append(orf(rng, rng.randint(600, 1500)))
        p.append(rastgele_dizi(rng.randint(300, 900), rng))
    p.append(rastgele_dizi(8000, rng))
    return "".join(p)


def mutasyona_ugrat(dizi: str, oran: float, rng: random.Random) -> str:
    ch = list(dizi)
    for i in range(len(ch)):
        if rng.random() < oran:
            ch[i] = rng.choice([b for b in BAZ if b != ch[i]])
    return "".join(ch)


def yaz_fasta(yol: Path, baslik: str, dizi: str) -> None:
    yol.parent.mkdir(parents=True, exist_ok=True)
    with yol.open("w") as f:
        f.write(f">{baslik}\n")
        for i in range(0, len(dizi), 70):
            f.write(dizi[i:i + 70] + "\n")


def _faj_ornekleri_indir() -> None:
    """pyGenomeViz'in Yersinia faj örnek veri kümesini (4 GenBank) faj/ altına kopyalar.

    Bu genomlar NCBI RefSeq'ten kamuya açıktır; pyGenomeViz
    https://github.com/moshi4/pygenomeviz-data-v1 üzerinden dağıtır.
    """
    hedef = CIKTI / "faj"
    hedef.mkdir(parents=True, exist_ok=True)
    if len(list(hedef.glob("*.gb*"))) >= 4:
        print(f"Faj örnekleri zaten var: {hedef}")
        return
    try:
        from pygenomeviz.utils import load_example_genbank_dataset
        import shutil

        for f in load_example_genbank_dataset("yersinia_phage"):
            shutil.copy(f, hedef / f.name)
        print(f"Faj örnekleri: {hedef} (4 GenBank, ~340 KB)")
    except Exception as e:
        print(f"!! Faj örnekleri indirilemedi ({e}). "
              f"Karşılaştırmalı örnek çalışmayabilir; internet gerektirir.")


def main() -> None:
    rng = random.Random(2026)
    genom = genom_kur(rng)
    yaz_fasta(CIKTI / "ornek_bakteri.fasta",
              "ornek_bakteri_kontig1 sentetik CRISPR demo genomu", genom)
    _faj_ornekleri_indir()

    # skani referansları
    yaz_fasta(REF / "Pseudomonas_biomine_A.fasta", "ref_A yakin", mutasyona_ugrat(genom, 0.008, rng))
    yaz_fasta(REF / "Pseudomonas_biomine_B.fasta", "ref_B orta", mutasyona_ugrat(genom, 0.06, rng))
    yaz_fasta(REF / "Acidithiobacillus_uzak_C.fasta", "ref_C uzak", mutasyona_ugrat(genom, 0.22, rng))

    print(f"Örnek genom: {CIKTI / 'ornek_bakteri.fasta'}  ({len(genom):,} bp)")
    print(f"Referans genomlar: {REF}  (3 adet)")
    print(f"Gömülü CRISPR: 28 bp tekrar, ~18 aralayıcı  (tekrar: {TEKRAR})")


if __name__ == "__main__":
    main()
