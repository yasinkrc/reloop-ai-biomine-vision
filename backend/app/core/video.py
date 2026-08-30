"""Video karesi çıkarımı — MP4/AVI dosyalarını belirli aralıklarla örnekler."""
from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.utils.loglama import log_al

log = log_al(__name__)


def kareleri_cikar(
    video_yolu: str | Path, aralik_sn: float = 2.0, maks_kare: int = 60
) -> list[tuple[int, float, np.ndarray]]:
    """(kare_indeksi, zaman_sn, rgb_goruntu) üçlülerinin listesini döndürür."""
    yakala = cv2.VideoCapture(str(video_yolu))
    if not yakala.isOpened():
        raise ValueError(f"Video açılamadı: {video_yolu}")

    fps = yakala.get(cv2.CAP_PROP_FPS) or 25.0
    toplam = int(yakala.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    adim = max(int(round(fps * aralik_sn)), 1)

    kareler: list[tuple[int, float, np.ndarray]] = []
    idx = 0
    alinan = 0
    while alinan < maks_kare:
        yakala.set(cv2.CAP_PROP_POS_FRAMES, idx)
        ok, kare = yakala.read()
        if not ok:
            break
        rgb = cv2.cvtColor(kare, cv2.COLOR_BGR2RGB)
        kareler.append((alinan, round(idx / fps, 2), rgb))
        alinan += 1
        idx += adim
        if toplam and idx >= toplam:
            break

    yakala.release()
    log.info(
        "Video örneklendi: %s → %d kare (fps=%.1f, aralık=%.1fs)",
        Path(video_yolu).name, len(kareler), fps, aralik_sn,
    )
    return kareler
