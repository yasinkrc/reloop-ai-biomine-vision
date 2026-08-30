"""Görüntü ön işleme: yükleme, gürültü azaltma, kontrast iyileştirme, kalite ölçümü.

Not: DMB AI Microscope'un ön işleme mantığı referans alınmış, kod kopyalanmadan
OpenCV/scikit-image ile yeniden yazılmıştır.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

DESTEKLENEN_UZANTILAR = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp"}


@dataclass
class OnIslemeCiktisi:
    orijinal_rgb: np.ndarray          # H,W,3  uint8
    islenmis_rgb: np.ndarray          # H,W,3  uint8  (model + segmentasyon girişi)
    gri: np.ndarray                   # H,W    uint8
    bulaniklik_skoru: float
    parlaklik: float
    gurultu_azaltma_uygulandi: bool
    kontrast_iyilestirme_uygulandi: bool
    orijinal_boyut: tuple[int, int]
    meta: dict = field(default_factory=dict)

    def ozet(self) -> dict:
        return {
            "gurultu_azaltma": self.gurultu_azaltma_uygulandi,
            "kontrast_iyilestirme": self.kontrast_iyilestirme_uygulandi,
            "bulaniklik_skoru": round(float(self.bulaniklik_skoru), 2),
            "parlaklik": round(float(self.parlaklik), 2),
            "orijinal_boyut": [int(self.orijinal_boyut[0]), int(self.orijinal_boyut[1])],
        }


def goruntu_oku(yol: str | Path) -> np.ndarray:
    """Diskteki bir görüntüyü RGB uint8 olarak okur (TIFF dâhil)."""
    yol = str(yol)
    if not Path(yol).is_file():
        raise FileNotFoundError(f"Görüntü dosyası bulunamadı: {yol}")
    veri = cv2.imread(yol, cv2.IMREAD_UNCHANGED)
    if veri is None:
        # Bazı TIFF'ler için imageio yedeği
        import imageio.v3 as iio

        veri = iio.imread(yol)
    return _rgb_uint8(veri)


def _rgb_uint8(veri: np.ndarray) -> np.ndarray:
    if veri.ndim == 2:
        veri = cv2.cvtColor(veri, cv2.COLOR_GRAY2RGB)
    elif veri.shape[2] == 4:
        veri = cv2.cvtColor(veri, cv2.COLOR_BGRA2RGB)
    elif veri.shape[2] == 3:
        # cv2.imread BGR verir; imageio zaten RGB. imread yolunu varsayıp çeviriyoruz.
        veri = cv2.cvtColor(veri, cv2.COLOR_BGR2RGB)

    if veri.dtype != np.uint8:
        veri = veri.astype(np.float32)
        alt, ust = float(np.nanmin(veri)), float(np.nanmax(veri))
        if ust > alt:
            veri = (veri - alt) / (ust - alt) * 255.0
        veri = np.clip(veri, 0, 255).astype(np.uint8)
    return np.ascontiguousarray(veri)


def bulaniklik_olc(gri: np.ndarray) -> float:
    """Laplacian varyansı — düşük değer = bulanık görüntü."""
    return float(cv2.Laplacian(gri, cv2.CV_64F).var())


def parlaklik_olc(gri: np.ndarray) -> float:
    return float(gri.mean())


def on_isle(
    goruntu_rgb: np.ndarray,
    *,
    gurultu_azaltma: bool = True,
    kontrast_iyilestirme: bool = True,
    maks_kenar: int = 1536,
) -> OnIslemeCiktisi:
    """Ana ön işleme hattı.

    - Çok büyük görüntüleri ölçekler (bellek/performans).
    - Non-local means ile gürültü azaltır.
    - CLAHE ile kontrastı iyileştirir.
    - Bulanıklık ve parlaklık skorlarını hesaplar.
    """
    orijinal = _rgb_uint8(goruntu_rgb)
    h, w = orijinal.shape[:2]
    orijinal_boyut = (h, w)

    calisma = orijinal.copy()
    olcek = min(1.0, maks_kenar / max(h, w))
    if olcek < 1.0:
        calisma = cv2.resize(
            calisma, (int(w * olcek), int(h * olcek)), interpolation=cv2.INTER_AREA
        )

    gri_ham = cv2.cvtColor(calisma, cv2.COLOR_RGB2GRAY)
    bulaniklik = bulaniklik_olc(gri_ham)
    parlaklik = parlaklik_olc(gri_ham)

    islenmis = calisma
    if gurultu_azaltma:
        islenmis = cv2.fastNlMeansDenoisingColored(islenmis, None, 5, 5, 7, 21)

    if kontrast_iyilestirme:
        lab = cv2.cvtColor(islenmis, cv2.COLOR_RGB2LAB)
        l, a, b = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        l = clahe.apply(l)
        islenmis = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2RGB)

    gri = cv2.cvtColor(islenmis, cv2.COLOR_RGB2GRAY)

    return OnIslemeCiktisi(
        orijinal_rgb=orijinal,
        islenmis_rgb=islenmis,
        gri=gri,
        bulaniklik_skoru=bulaniklik,
        parlaklik=parlaklik,
        gurultu_azaltma_uygulandi=gurultu_azaltma,
        kontrast_iyilestirme_uygulandi=kontrast_iyilestirme,
        orijinal_boyut=orijinal_boyut,
        meta={"olcek": olcek},
    )
