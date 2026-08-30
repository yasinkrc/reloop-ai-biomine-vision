"""Sınıflandırıcı ve Grad-CAM testleri (PyTorch gerektirir)."""
from __future__ import annotations

import numpy as np
import pytest

torch = pytest.importorskip("torch")

from app.core.grad_cam import GradCAM  # noqa: E402
from app.ml import siniflar  # noqa: E402
from app.ml.siniflandirici import Siniflandirici  # noqa: E402


@pytest.fixture(scope="module")
def siniflandirici() -> Siniflandirici:
    # Ağırlık dosyası olmadan: eğitilmemiş model.
    return Siniflandirici(model_yolu=None, cihaz="cpu")


def test_tahmin_sekli_ve_alanlari(siniflandirici, cubuk_gorsel):
    s = siniflandirici.tahmin_et(cubuk_gorsel, guven_dusuk_esik=55.0)
    assert 0 <= s.guven <= 100
    assert len(s.ilk_bes) == 5
    assert abs(sum(o for _, o in s.ilk_bes) - 100) < 60  # ilk-5 toplamı makul
    assert s.egitilmedi is True
    # Eğitilmemiş model her zaman "desteklenmiyor" işaretlenir.
    assert s.desteklenmiyor is True
    assert s.sinif_etiketi == siniflar.DESTEKLENMEYEN_ETIKET


def test_ilk_bes_azalan_sirada(siniflandirici, cubuk_gorsel):
    s = siniflandirici.tahmin_et(cubuk_gorsel)
    olasiliklar = [o for _, o in s.ilk_bes]
    assert olasiliklar == sorted(olasiliklar, reverse=True)


def test_gradcam_isi_haritasi(siniflandirici, cubuk_gorsel):
    isi = GradCAM(siniflandirici).isi_haritasi(cubuk_gorsel)
    assert isi.ndim == 2
    assert isi.min() >= 0.0 and isi.max() <= 1.0


def test_sinif_listesi_tutarli():
    assert len(siniflar.SINIFLAR) == len(set(siniflar.SINIFLAR))
    for s in siniflar.SINIFLAR:
        assert s in siniflar.SINIF_ETIKETLERI
