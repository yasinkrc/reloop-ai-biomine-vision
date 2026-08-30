"""Segmentasyon + morfoloji birim testleri."""
from __future__ import annotations

import numpy as np

from app.core import morfoloji, on_isleme, segmentasyon


def test_segmentasyon_hucre_bulur(cubuk_gorsel):
    on = on_isleme.on_isle(cubuk_gorsel)
    seg = segmentasyon.segmentle(on.gri, omnipose_kullan=False)
    assert seg.hucre_sayisi >= 5
    assert seg.yontem == "klasik-watershed"
    assert seg.etiket_haritasi.shape == on.gri.shape


def test_bos_goruntude_az_hucre(bos_gorsel):
    on = on_isleme.on_isle(bos_gorsel)
    seg = segmentasyon.segmentle(on.gri, omnipose_kullan=False)
    assert seg.hucre_sayisi <= 2


def test_morfoloji_olcumleri_makul(cubuk_gorsel):
    on = on_isleme.on_isle(cubuk_gorsel)
    seg = segmentasyon.segmentle(on.gri, omnipose_kullan=False)
    olcumler, ozet = morfoloji.olc(seg.etiket_haritasi)
    assert len(olcumler) == ozet.hucre_sayisi
    assert 0 <= ozet.kaplama_orani <= 100
    assert ozet.ort_hucre_alani > 0
    assert ozet.baskin_morfoloji in {"cubuk", "kuresel", "filamentli", "karisik", "bilinmiyor"}
    for o in olcumler:
        assert o.uzunluk >= o.genislik > 0
        assert 0 <= o.dairesellik <= 1
        assert len(o.renk) == 3


def test_her_hucreye_renk_atanir():
    # 3 ayrı blok
    etiket = np.zeros((60, 120), np.int32)
    etiket[10:30, 10:30] = 1
    etiket[10:30, 50:70] = 2
    etiket[10:30, 90:110] = 3
    olcumler, ozet = morfoloji.olc(etiket)
    assert ozet.hucre_sayisi == 3
    renkler = {tuple(o.renk) for o in olcumler}
    assert len(renkler) == 3
