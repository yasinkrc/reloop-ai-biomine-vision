"""İşaretlenmiş analiz görüntüsü üretimi.

Her hücrenin çevresi kendi renginde çizilir, merkezine sıra numarası
yazılır ve üst köşeye toplam hücre sayısı bilgisi eklenir.
"""
from __future__ import annotations

import cv2
import numpy as np

from app.core.morfoloji import HucreOlcumu


def isaretli_gorsel_uret(
    taban_rgb: np.ndarray,
    etiket_haritasi: np.ndarray,
    olcumler: list[HucreOlcumu],
    *,
    numara_yaz: bool = True,
) -> np.ndarray:
    """Segmentasyon konturlarını taban görüntü üzerine renkli çizer."""
    gorsel = taban_rgb.copy()
    if gorsel.shape[:2] != etiket_haritasi.shape[:2]:
        gorsel = cv2.resize(
            gorsel,
            (etiket_haritasi.shape[1], etiket_haritasi.shape[0]),
            interpolation=cv2.INTER_LINEAR,
        )

    renk_haritasi = {o.id: o.renk for o in olcumler}
    kapli = np.zeros_like(gorsel)

    for etiket in range(1, int(etiket_haritasi.max()) + 1):
        maske = (etiket_haritasi == etiket).astype(np.uint8)
        if maske.sum() == 0:
            continue
        renk = renk_haritasi.get(etiket, (255, 0, 0))
        konturlar, _ = cv2.findContours(
            maske, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )
        cv2.drawContours(gorsel, konturlar, -1, renk, 2)
        cv2.drawContours(kapli, konturlar, -1, renk, thickness=cv2.FILLED)

    # Hafif yarı saydam dolgu ile hücreleri vurgula.
    gorsel = cv2.addWeighted(gorsel, 1.0, kapli, 0.18, 0)

    if numara_yaz:
        for o in olcumler:
            x, y = int(o.merkez[0]), int(o.merkez[1])
            cv2.putText(
                gorsel, str(o.id), (x - 4, y + 4),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (255, 255, 255), 1, cv2.LINE_AA
            )

    _bilgi_serit(gorsel, f"Toplam hucre: {len(olcumler)}")
    return gorsel


def _bilgi_serit(gorsel: np.ndarray, metin: str) -> None:
    h, w = gorsel.shape[:2]
    serit_h = max(24, h // 22)
    cv2.rectangle(gorsel, (0, 0), (w, serit_h), (20, 20, 20), thickness=cv2.FILLED)
    cv2.putText(
        gorsel, metin, (8, int(serit_h * 0.7)),
        cv2.FONT_HERSHEY_SIMPLEX, serit_h / 42.0, (255, 255, 255), 1, cv2.LINE_AA
    )


def isi_haritasi_bindir(taban_rgb: np.ndarray, isi: np.ndarray) -> np.ndarray:
    """Grad-CAM ısı haritasını taban görüntü ile harmanlar."""
    isi = np.clip(isi, 0, 1)
    isi_u8 = (isi * 255).astype(np.uint8)
    if isi_u8.shape[:2] != taban_rgb.shape[:2]:
        isi_u8 = cv2.resize(isi_u8, (taban_rgb.shape[1], taban_rgb.shape[0]))
    renkli = cv2.applyColorMap(isi_u8, cv2.COLORMAP_JET)
    renkli = cv2.cvtColor(renkli, cv2.COLOR_BGR2RGB)
    return cv2.addWeighted(taban_rgb, 0.55, renkli, 0.45, 0)
