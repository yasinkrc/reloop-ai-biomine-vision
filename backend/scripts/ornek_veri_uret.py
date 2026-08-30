#!/usr/bin/env python3
"""Sentetik örnek mikroskop görüntüleri üretir.

Gerçek bir etiketli biyoliç veri kümesi paylaşım kısıtlıdır; bu betik,
demo ve DEMO modelin eğitimi için her sınıfa karşılık gelen sentetik
faz-kontrast benzeri görüntüler üretir (çubuk / kok / filament / biyofilm
/ karışık / düşük biyokütle). Üretimde kontrollü rastgelelik kullanılır.

Kullanım:
    python scripts/ornek_veri_uret.py --cikti ornek_veri --sinif_basi 40
"""
from __future__ import annotations

import argparse
import math
import random
from pathlib import Path

import cv2
import numpy as np

BOYUT = 512


def _zemin(rng: random.Random) -> np.ndarray:
    taban = rng.randint(150, 205)
    img = np.full((BOYUT, BOYUT, 3), taban, np.uint8)
    gurultu = np.random.default_rng(rng.randint(0, 1 << 30)).normal(
        0, 6, (BOYUT, BOYUT, 3)
    )
    img = np.clip(img.astype(np.float32) + gurultu, 0, 255).astype(np.uint8)
    # hafif aydınlatma gradyanı
    gy, gx = np.mgrid[0:BOYUT, 0:BOYUT]
    grad = ((gx + gy) / (2 * BOYUT) * 30 - 15).astype(np.float32)
    img = np.clip(img.astype(np.float32) + grad[..., None], 0, 255).astype(np.uint8)
    return img


def _cizgi_hucre(img, merkez, aci, uzunluk, kalinlik, koyu):
    x, y = merkez
    dx, dy = math.cos(aci), math.sin(aci)
    p1 = (int(x - dx * uzunluk / 2), int(y - dy * uzunluk / 2))
    p2 = (int(x + dx * uzunluk / 2), int(y + dy * uzunluk / 2))
    cv2.line(img, p1, p2, (koyu, koyu, koyu), kalinlik, cv2.LINE_AA)
    cv2.line(img, p1, p2, (min(koyu + 40, 255),) * 3, max(kalinlik - 3, 1), cv2.LINE_AA)


def _kok_hucre(img, merkez, r, koyu):
    cv2.circle(img, merkez, r, (koyu, koyu, koyu), -1, cv2.LINE_AA)
    cv2.circle(img, merkez, max(r - 2, 1), (min(koyu + 50, 255),) * 3, -1, cv2.LINE_AA)


def uret(sinif: str, rng: random.Random) -> np.ndarray:
    img = _zemin(rng)
    koyu = rng.randint(60, 110)

    if sinif == "cubuk_bakteri_yogun":
        for _ in range(rng.randint(120, 200)):
            _cizgi_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                         rng.uniform(0, math.pi), rng.randint(16, 30),
                         rng.randint(5, 8), koyu)
    elif sinif == "cubuk_bakteri_seyrek":
        for _ in range(rng.randint(12, 30)):
            _cizgi_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                         rng.uniform(0, math.pi), rng.randint(16, 28),
                         rng.randint(5, 8), koyu)
    elif sinif == "kok_bakteri_kume":
        for _ in range(rng.randint(6, 12)):
            cx, cy = rng.randint(60, BOYUT - 60), rng.randint(60, BOYUT - 60)
            for _ in range(rng.randint(8, 20)):
                _kok_hucre(img, (cx + rng.randint(-25, 25), cy + rng.randint(-25, 25)),
                           rng.randint(6, 10), koyu)
    elif sinif == "kok_bakteri_zincir":
        for _ in range(rng.randint(6, 14)):
            cx, cy = rng.randint(40, BOYUT - 40), rng.randint(40, BOYUT - 40)
            aci = rng.uniform(0, math.pi)
            for k in range(rng.randint(5, 12)):
                _kok_hucre(img, (int(cx + math.cos(aci) * k * 16),
                                 int(cy + math.sin(aci) * k * 16)),
                           rng.randint(6, 9), koyu)
    elif sinif == "filamentli_organizma":
        for _ in range(rng.randint(6, 16)):
            x, y = rng.randint(30, BOYUT - 30), rng.randint(30, BOYUT - 30)
            aci = rng.uniform(0, math.pi)
            for k in range(rng.randint(20, 40)):
                aci += rng.uniform(-0.15, 0.15)
                nx, ny = int(x + math.cos(aci) * 8), int(y + math.sin(aci) * 8)
                cv2.line(img, (x, y), (nx, ny), (koyu,) * 3, rng.randint(3, 5), cv2.LINE_AA)
                x, y = nx, ny
    elif sinif == "biyofilm_matriks":
        maske = np.zeros((BOYUT, BOYUT), np.uint8)
        for _ in range(rng.randint(3, 6)):
            cv2.circle(maske, (rng.randint(80, BOYUT - 80), rng.randint(80, BOYUT - 80)),
                       rng.randint(70, 130), 255, -1)
        maske = cv2.GaussianBlur(maske, (0, 0), 25)
        img[maske > 60] = (img[maske > 60].astype(np.float32) * 0.7).astype(np.uint8)
        for _ in range(rng.randint(60, 110)):
            _cizgi_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                         rng.uniform(0, math.pi), rng.randint(10, 18), rng.randint(4, 6), koyu)
    elif sinif == "karisik_kultur":
        for _ in range(rng.randint(30, 60)):
            _cizgi_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                         rng.uniform(0, math.pi), rng.randint(16, 28), rng.randint(5, 8), koyu)
        for _ in range(rng.randint(30, 60)):
            _kok_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                       rng.randint(6, 10), koyu)
    elif sinif == "dusuk_biyokutle":
        for _ in range(rng.randint(0, 3)):
            _cizgi_hucre(img, (rng.randint(20, BOYUT - 20), rng.randint(20, BOYUT - 20)),
                         rng.uniform(0, math.pi), rng.randint(16, 24), rng.randint(5, 7), koyu)
    else:
        raise ValueError(f"Bilinmeyen sınıf: {sinif}")

    img = cv2.GaussianBlur(img, (3, 3), 0)
    return img


def main() -> None:
    from app.ml.siniflar import SINIFLAR

    ap = argparse.ArgumentParser()
    ap.add_argument("--cikti", default="ornek_veri")
    ap.add_argument("--sinif_basi", type=int, default=40)
    ap.add_argument("--tohum", type=int, default=42)
    ap.add_argument("--demo_kopya", type=int, default=1,
                    help="Kök dizine kaç adet hızlı demo görüntüsü kopyalansın")
    args = ap.parse_args()

    kok = Path(__file__).resolve().parent.parent
    cikti = (kok / args.cikti).resolve()
    for sinif in SINIFLAR:
        (cikti / sinif).mkdir(parents=True, exist_ok=True)
        rng = random.Random(f"{args.tohum}-{sinif}")
        for i in range(args.sinif_basi):
            img = uret(sinif, rng)
            cv2.imwrite(str(cikti / sinif / f"{sinif}_{i:03d}.png"), img)
        # kök dizine hızlı-demo örneği
        for j in range(args.demo_kopya):
            img = uret(sinif, random.Random(f"demo-{sinif}-{j}"))
            cv2.imwrite(str(cikti / f"{sinif}_{j:02d}.png"), img)
        print(f"  {sinif}: {args.sinif_basi} görüntü")

    print(f"Örnek veri üretildi: {cikti}")


if __name__ == "__main__":
    import sys

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    main()
