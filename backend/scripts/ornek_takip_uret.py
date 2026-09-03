#!/usr/bin/env python3
"""Örnek hücre-takibi zaman serisi üretir (sentetik time-lapse).

~14 kare, 512 px. Çubuk hücreler rastgele yürüyüşle sürüklenir; 2 hücre
sekans ortasında bölünür. Sonuç: `ornek_veri/takip/takip_demo.mp4`.

Kullanım:  python scripts/ornek_takip_uret.py
"""
from __future__ import annotations

import math
import random
import zipfile
from pathlib import Path

import cv2
import numpy as np

KOK = Path(__file__).resolve().parent.parent
CIKTI = KOK / "ornek_veri" / "takip"
BOYUT = 512
KARE = 24


def _zemin(rng: random.Random) -> np.ndarray:
    # Neredeyse düz zemin — sentetik demo; hafif doku PNG sıkıştırmasını bozmaz.
    img = np.full((BOYUT, BOYUT, 3), 198, np.uint8)
    g = np.random.default_rng(rng.randint(0, 1 << 30)).normal(0, 1.2, (BOYUT, BOYUT, 3))
    return np.clip(img.astype(np.float32) + g, 0, 255).astype(np.uint8)


def _ciz(img, x, y, aci, r=11, koyu=70):
    """Yuvarlak (kok) hücre — watershed kare kare temiz ayırır."""
    cv2.circle(img, (int(x), int(y)), r, (koyu, koyu, koyu), -1, cv2.LINE_AA)
    cv2.circle(img, (int(x), int(y)), max(r - 3, 2), (min(koyu + 55, 255),) * 3,
               -1, cv2.LINE_AA)


def main() -> None:
    CIKTI.mkdir(parents=True, exist_ok=True)
    rng = random.Random(7)
    # 3x3 ızgarada iyi ayrılmış 9 hücre — segmentasyon kare kare temiz olsun
    hucreler = []
    for gy in range(3):
        for gx in range(3):
            hucreler.append({
                "x": 110 + gx * 145 + rng.uniform(-12, 12),
                "y": 110 + gy * 145 + rng.uniform(-12, 12),
                "aci": rng.uniform(0, math.pi), "b": None,
            })

    yaz = cv2.VideoWriter(str(CIKTI / "takip_demo.mp4"),
                          cv2.VideoWriter_fourcc(*"mp4v"), 8, (BOYUT, BOYUT))
    kare_yollari = []
    for k in range(KARE):
        img = _zemin(rng)
        # bölünme: 8 ve 15. karede birer hücre belirgin biçimde ikiye ayrılsın
        if k in (8, 15):
            idx = 4 if k == 8 else 1
            if idx < len(hucreler):
                h = hucreler[idx]
                hucreler.append({"x": h["x"] + 18, "y": h["y"] + 3,
                                 "aci": h["aci"], "b": idx})
                h["x"] -= 18
        for h in hucreler:
            h["x"] = float(np.clip(h["x"] + rng.uniform(-3, 3), 30, BOYUT - 30))
            h["y"] = float(np.clip(h["y"] + rng.uniform(-3, 3), 30, BOYUT - 30))
            h["aci"] += rng.uniform(-0.12, 0.12)
            _ciz(img, h["x"], h["y"], h["aci"])
        img = cv2.GaussianBlur(img, (3, 3), 0.6)
        yol = CIKTI / f"kare_{k:02d}.jpg"
        cv2.imwrite(str(yol), img, [cv2.IMWRITE_JPEG_QUALITY, 85])
        kare_yollari.append(yol)
        yaz.write(img)
    yaz.release()

    # Kare karelerin ZIP'i — /api/takip/ornek bunu kullanır (ardışık kareler,
    # eşleme çok daha güvenilir olur).
    with zipfile.ZipFile(CIKTI / "takip_demo_kareler.zip", "w") as z:
        for p in kare_yollari:
            z.write(p, arcname=p.name)

    print(f"Örnek zaman serisi: {CIKTI / 'takip_demo.mp4'}  ({KARE} kare, 8 fps)")
    print(f"Kare ZIP (ornek endpoint): {CIKTI / 'takip_demo_kareler.zip'}")


if __name__ == "__main__":
    main()
