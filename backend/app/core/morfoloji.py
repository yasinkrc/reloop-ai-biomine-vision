"""Morfolojik ölçümler ve hücre şekli (çubuk / küresel / filamentli) tahmini.

Her etiketli hücre için alan, uzunluk (majör eksen), genişlik (minör eksen),
dairesellik ve en/boy oranı hesaplanır. Bu ölçülerden hücre morfolojisi
sınıflandırılır ve görüntü genelinde baskın morfoloji belirlenir.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
from skimage.measure import regionprops

# Her hücreye görselde farklı renk verebilmek için sabit bir palet.
PALET = [
    (230, 25, 75), (60, 180, 75), (255, 225, 25), (0, 130, 200),
    (245, 130, 48), (145, 30, 180), (70, 240, 240), (240, 50, 230),
    (210, 245, 60), (250, 190, 212), (0, 128, 128), (220, 190, 255),
    (170, 110, 40), (255, 250, 200), (128, 0, 0), (170, 255, 195),
    (128, 128, 0), (255, 215, 180), (0, 0, 128), (128, 128, 128),
]


@dataclass
class HucreOlcumu:
    id: int
    alan: float
    uzunluk: float
    genislik: float
    dairesellik: float
    en_boy_orani: float
    morfoloji: str
    merkez: tuple[float, float]
    renk: tuple[int, int, int]

    def sozluk(self) -> dict:
        d = asdict(self)
        d["merkez"] = [round(float(x), 1) for x in self.merkez]
        d["renk"] = list(self.renk)
        for k in ("alan", "uzunluk", "genislik", "dairesellik", "en_boy_orani"):
            d[k] = round(float(d[k]), 3)
        return d


@dataclass
class MorfolojiOzeti:
    hucre_sayisi: int
    kaplama_orani: float
    ort_hucre_alani: float
    ort_uzunluk: float
    ort_genislik: float
    ort_dairesellik: float
    baskin_morfoloji: str
    morfoloji_dagilimi: dict[str, int]

    def sozluk(self) -> dict:
        d = asdict(self)
        for k in ("kaplama_orani", "ort_hucre_alani", "ort_uzunluk",
                  "ort_genislik", "ort_dairesellik"):
            d[k] = round(float(d[k]), 3)
        return d


def _morfoloji_sinifla(en_boy: float, dairesellik: float, uzunluk: float,
                       ort_uzunluk: float) -> str:
    """Tek hücre için kaba morfoloji sınıfı."""
    if en_boy >= 3.5 or (uzunluk > 2.2 * max(ort_uzunluk, 1e-6) and en_boy >= 2.8):
        return "filamentli"
    if en_boy <= 1.35 and dairesellik >= 0.80:
        return "kuresel"
    return "cubuk"


def olc(etiket_haritasi: np.ndarray) -> tuple[list[HucreOlcumu], MorfolojiOzeti]:
    h, w = etiket_haritasi.shape[:2]
    toplam_piksel = float(h * w)
    bolgeler = [b for b in regionprops(etiket_haritasi) if b.area > 0]

    olcumler: list[HucreOlcumu] = []
    uzunluklar = [max(b.axis_major_length, 1e-6) for b in bolgeler]
    ort_uzunluk_ham = float(np.mean(uzunluklar)) if uzunluklar else 0.0

    kaplanan = 0.0
    for i, b in enumerate(bolgeler):
        majör = float(b.axis_major_length)
        minör = float(max(b.axis_minor_length, 1e-6))
        cevre = float(b.perimeter) if b.perimeter else 0.0
        dairesellik = (
            float(4.0 * np.pi * b.area / (cevre * cevre)) if cevre > 0 else 0.0
        )
        dairesellik = min(dairesellik, 1.0)
        en_boy = majör / minör
        morf = _morfoloji_sinifla(en_boy, dairesellik, majör, ort_uzunluk_ham)
        kaplanan += float(b.area)
        olcumler.append(
            HucreOlcumu(
                id=i + 1,
                alan=float(b.area),
                uzunluk=majör,
                genislik=minör,
                dairesellik=dairesellik,
                en_boy_orani=en_boy,
                morfoloji=morf,
                merkez=(float(b.centroid[1]), float(b.centroid[0])),  # x, y
                renk=PALET[i % len(PALET)],
            )
        )

    dagilim = {"cubuk": 0, "kuresel": 0, "filamentli": 0}
    for o in olcumler:
        dagilim[o.morfoloji] += 1

    if olcumler:
        baskin, baskin_sayi = max(dagilim.items(), key=lambda kv: kv[1])
        # Belirgin ikinci bir morfoloji varsa "karisik".
        if baskin_sayi / len(olcumler) < 0.6 and len(olcumler) >= 4:
            baskin_morf = "karisik"
        else:
            baskin_morf = baskin
    else:
        baskin_morf = "bilinmiyor"

    ozet = MorfolojiOzeti(
        hucre_sayisi=len(olcumler),
        kaplama_orani=100.0 * kaplanan / toplam_piksel,
        ort_hucre_alani=float(np.mean([o.alan for o in olcumler])) if olcumler else 0.0,
        ort_uzunluk=float(np.mean([o.uzunluk for o in olcumler])) if olcumler else 0.0,
        ort_genislik=float(np.mean([o.genislik for o in olcumler])) if olcumler else 0.0,
        ort_dairesellik=(
            float(np.mean([o.dairesellik for o in olcumler])) if olcumler else 0.0
        ),
        baskin_morfoloji=baskin_morf,
        morfoloji_dagilimi=dagilim,
    )
    return olcumler, ozet
