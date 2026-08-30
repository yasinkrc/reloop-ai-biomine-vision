"""Bakteri segmentasyonu.

Birincil yöntem: **Omnipose** (kevinjohncutler/omnipose, MIT lisanslı) yerleşik
`bact_phase_omni` / `bact_fluor_omni` pretrained modelleri ile hücrelerin
birbirinden ayrılması.

Omnipose kurulu değilse veya model yüklenemezse sistem otomatik olarak
klasik bir yönteme (Otsu eşikleme + mesafe dönüşümü + watershed) düşer ve
çalışmaya devam eder. Hangi yöntemin kullanıldığı sonuçta raporlanır.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.utils.loglama import log_al

log = log_al(__name__)

_omnipose_model = None
_omnipose_denendi = False


@dataclass
class SegmentasyonSonucu:
    etiket_haritasi: np.ndarray   # H,W  int32  (0 = arka plan, 1..N = hücreler)
    yontem: str                   # "omnipose:<model>" | "klasik-watershed"
    hucre_sayisi: int


def _omnipose_yukle(model_adi: str):
    global _omnipose_model, _omnipose_denendi
    if _omnipose_denendi:
        return _omnipose_model
    _omnipose_denendi = True
    try:
        from cellpose_omni import models as omni_models  # type: ignore

        _omnipose_model = omni_models.CellposeModel(
            gpu=_cuda_var(), model_type=model_adi
        )
        log.info("Omnipose modeli yüklendi: %s", model_adi)
    except Exception as e:  # pragma: no cover - ortam bağımlı
        log.warning(
            "Omnipose yüklenemedi (%s). Klasik segmentasyona düşülüyor.", e
        )
        _omnipose_model = None
    return _omnipose_model


def _cuda_var() -> bool:
    try:
        import torch

        return torch.cuda.is_available()
    except Exception:
        return False


def _omnipose_ile_segmentle(gri: np.ndarray, model_adi: str) -> np.ndarray | None:
    model = _omnipose_yukle(model_adi)
    if model is None:
        return None
    try:
        sonuc = model.eval(
            gri,
            channels=[0, 0],
            diameter=None,
            omni=True,
            resample=True,
            verbose=False,
        )
        maske = sonuc[0]
        return np.asarray(maske, dtype=np.int32)
    except Exception as e:  # pragma: no cover
        log.warning("Omnipose çıkarımı başarısız (%s). Klasik yönteme düşülüyor.", e)
        return None


def _klasik_watershed(gri: np.ndarray) -> np.ndarray:
    """Omnipose yoksa kullanılan yedek segmentasyon."""
    import cv2
    from scipy import ndimage as ndi
    from skimage.feature import peak_local_max
    from skimage.segmentation import watershed

    bulanik = cv2.GaussianBlur(gri, (7, 7), 0)
    # Arka planın koyu mu açık mı olduğunu tahmin et.
    if bulanik.mean() > 127:
        _, ikili = cv2.threshold(
            bulanik, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU
        )
    else:
        _, ikili = cv2.threshold(
            bulanik, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU
        )

    cekirdek = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    ikili = cv2.morphologyEx(ikili, cv2.MORPH_OPEN, cekirdek, iterations=2)
    ikili = cv2.morphologyEx(ikili, cv2.MORPH_CLOSE, cekirdek, iterations=1)

    mesafe = ndi.distance_transform_edt(ikili > 0)
    if mesafe.max() <= 0:
        return np.zeros_like(gri, dtype=np.int32)

    koordinatlar = peak_local_max(
        mesafe, min_distance=11, labels=(ikili > 0), exclude_border=False
    )
    tepe_maskesi = np.zeros(mesafe.shape, dtype=bool)
    if len(koordinatlar):
        tepe_maskesi[tuple(koordinatlar.T)] = True
    isaretler, _ = ndi.label(tepe_maskesi)
    etiketler = watershed(-mesafe, isaretler, mask=(ikili > 0))
    return etiketler.astype(np.int32)


def _kucuk_nesneleri_ele(etiketler: np.ndarray, min_alan: int = 12) -> np.ndarray:
    from skimage.measure import regionprops

    temiz = etiketler.copy()
    for bolge in regionprops(etiketler):
        if bolge.area < min_alan:
            temiz[etiketler == bolge.label] = 0
    # Etiketleri yeniden sırala (1..N)
    from skimage.segmentation import relabel_sequential

    temiz, _, _ = relabel_sequential(temiz)
    return temiz.astype(np.int32)


def segmentle(
    gri: np.ndarray,
    *,
    omnipose_model: str = "bact_phase_omni",
    omnipose_kullan: bool = True,
    min_hucre_alani: int = 12,
) -> SegmentasyonSonucu:
    """Gri tonlamalı görüntüden hücre etiket haritası üretir."""
    etiketler = None
    yontem = "klasik-watershed"

    if omnipose_kullan:
        etiketler = _omnipose_ile_segmentle(gri, omnipose_model)
        if etiketler is not None:
            yontem = f"omnipose:{omnipose_model}"

    if etiketler is None:
        etiketler = _klasik_watershed(gri)

    etiketler = _kucuk_nesneleri_ele(etiketler, min_hucre_alani)
    sayi = int(etiketler.max())
    log.info("Segmentasyon tamam — yöntem=%s hücre=%d", yontem, sayi)
    return SegmentasyonSonucu(etiket_haritasi=etiketler, yontem=yontem, hucre_sayisi=sayi)
