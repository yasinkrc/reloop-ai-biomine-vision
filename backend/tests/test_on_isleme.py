"""Ön işleme birim testleri."""
from __future__ import annotations

import numpy as np

from app.core import on_isleme


def test_on_isle_temel_ciktilar(cubuk_gorsel):
    c = on_isleme.on_isle(cubuk_gorsel)
    assert c.islenmis_rgb.shape == cubuk_gorsel.shape
    assert c.gri.ndim == 2
    assert c.gurultu_azaltma_uygulandi and c.kontrast_iyilestirme_uygulandi
    assert c.bulaniklik_skoru > 0
    assert 0 <= c.parlaklik <= 255


def test_bulaniklik_skoru_ayirt_ediyor(cubuk_gorsel, karanlik_bulanik_gorsel):
    net = on_isleme.on_isle(cubuk_gorsel)
    bulanik = on_isleme.on_isle(karanlik_bulanik_gorsel)
    assert net.bulaniklik_skoru > bulanik.bulaniklik_skoru
    assert bulanik.parlaklik < net.parlaklik


def test_buyuk_goruntu_olceklenir():
    dev = (np.random.default_rng(1).random((3000, 4000, 3)) * 255).astype(np.uint8)
    c = on_isleme.on_isle(dev, maks_kenar=1024)
    assert max(c.islenmis_rgb.shape[:2]) <= 1024
    assert tuple(c.orijinal_boyut) == (3000, 4000)


def test_16bit_goruntu_normalize_edilir():
    g16 = (np.random.default_rng(2).random((64, 64)) * 65535).astype(np.uint16)
    rgb = on_isleme._rgb_uint8(g16)
    assert rgb.dtype == np.uint8 and rgb.shape == (64, 64, 3)
