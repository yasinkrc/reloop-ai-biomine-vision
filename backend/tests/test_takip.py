"""Hücre takibi (cell tracking) testleri."""
from __future__ import annotations

import zipfile
from pathlib import Path

import cv2
import numpy as np
import pytest

pytest.importorskip("scipy")

from app.core import takip as T  # noqa: E402


def _zaman_serisi_zip(tmp_path: Path, kare: int = 10, hucre: int = 6) -> Path:
    rng = np.random.default_rng(0)
    merkezler = np.column_stack([
        rng.uniform(80, 432, hucre), rng.uniform(80, 432, hucre)
    ])
    kare_dizin = tmp_path / "kareler"
    kare_dizin.mkdir()
    yollar = []
    for k in range(kare):
        img = np.full((512, 512, 3), 200, np.uint8)
        merkezler += rng.uniform(-3, 3, merkezler.shape)
        for (x, y) in merkezler:
            cv2.circle(img, (int(x), int(y)), 11, (70, 70, 70), -1)
        p = kare_dizin / f"k{k:02d}.png"
        cv2.imwrite(str(p), img)
        yollar.append(p)
    zp = tmp_path / "seri.zip"
    with zipfile.ZipFile(zp, "w") as z:
        for p in yollar:
            z.write(p, arcname=p.name)
    return zp


def test_takip_uctan_uca(tmp_path):
    zp = _zaman_serisi_zip(tmp_path, kare=10, hucre=6)
    d = T.takip_analiz(zp, aralik_sn=0.5, dosya_adi="seri.zip")
    assert d["kare_sayisi"] == 10
    assert d["yontem"] in {"trackastra", "yerlesik-iou"}
    assert d["iz_sayisi"] >= 3
    assert len(d["zaman_serisi"]) == 10
    assert d["kaplama_video"] and d["csv_rapor"] and d["json_rapor"]
    assert d["aciklama"]


def test_yerlesik_takip_izleri_baglar(tmp_path):
    """trackastra devre dışıyken yerleşik IoU takibi izleri kareler arası bağlamalı."""
    zp = _zaman_serisi_zip(tmp_path, kare=8, hucre=5)
    T_orig = T._trackastra_takip
    T._trackastra_takip = lambda *a, **k: None
    try:
        d = T.takip_analiz(zp, aralik_sn=0.5)
    finally:
        T._trackastra_takip = T_orig
    assert d["yontem"] == "yerlesik-iou"
    # 5 hücre 8 kare — çoğu iz 2+ kare sürmeli
    assert d["uzun_iz_sayisi"] >= 3


def test_az_kare_hata(tmp_path):
    zp = _zaman_serisi_zip(tmp_path, kare=1, hucre=4)
    with pytest.raises(ValueError):
        T.takip_analiz(zp)
