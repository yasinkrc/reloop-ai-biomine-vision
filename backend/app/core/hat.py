"""Uçtan uca analiz hattı (pipeline).

Tek bir görüntü için: ön işleme → segmentasyon (Omnipose) → morfoloji →
sınıflandırma → Grad-CAM → işaretleme → kural motoru → sonuç sözlüğü.
"""
from __future__ import annotations

import datetime as dt
from pathlib import Path
from typing import Any

import numpy as np

from app.config import ayarlari_al
from app.core import grad_cam as gc
from app.core import isaretleme, morfoloji, on_isleme, segmentasyon, uyari_motoru
from app.ml.siniflandirici import siniflandiriciyi_al
from app.utils.dosya import gorsel_yaz, rel
from app.utils.loglama import log_al

log = log_al(__name__)


def tek_gorsel_analiz(
    goruntu_yolu: str | Path,
    esikler: dict[str, Any],
    *,
    gradcam: bool = True,
    onceki_hucre_sayisi: int | None = None,
    kare_indeksi: int = 0,
    kare_zamani_sn: float = 0.0,
    on_isleme_ayar: dict | None = None,
) -> dict[str, Any]:
    ayar = ayarlari_al()
    on_isleme_ayar = on_isleme_ayar or {}

    ham = on_isleme.goruntu_oku(goruntu_yolu)
    on = on_isleme.on_isle(
        ham,
        gurultu_azaltma=on_isleme_ayar.get("gurultu_azaltma", True),
        kontrast_iyilestirme=on_isleme_ayar.get("kontrast_iyilestirme", True),
    )

    seg = segmentasyon.segmentle(
        on.gri,
        omnipose_model=ayar.omnipose_model,
        omnipose_kullan=on_isleme_ayar.get("omnipose_kullan", True),
    )
    olcumler, morf_ozet = morfoloji.olc(seg.etiket_haritasi)

    sinif = siniflandiriciyi_al()
    tahmin = sinif.tahmin_et(on.islenmis_rgb, guven_dusuk_esik=esikler["guven_dusuk"])

    # İşaretlenmiş görüntü
    isaretli = isaretleme.isaretli_gorsel_uret(
        on.islenmis_rgb, seg.etiket_haritasi, olcumler
    )

    # Grad-CAM
    gradcam_yolu = None
    if gradcam:
        isi = gc.GradCAM(sinif).isi_haritasi(on.islenmis_rgb)
        gradcam_rgb = isaretleme.isi_haritasi_bindir(on.islenmis_rgb, isi)
        gradcam_yolu = gorsel_yaz(gradcam_rgb, ayar.cikti_dizini, on_ek="gradcam_")

    # Kural motoru
    uyarilar = uyari_motoru.uyarilari_uret(
        on, morf_ozet, tahmin, esikler, onceki_hucre_sayisi=onceki_hucre_sayisi
    )
    risk = uyari_motoru.risk_seviyesi(uyarilar, esikler)
    aciklama = uyari_motoru.aciklama_uret(
        morf_ozet, tahmin, uyarilar, seg.yontem, risk
    )

    orijinal_yolu = gorsel_yaz(on.orijinal_rgb, ayar.cikti_dizini, on_ek="orijinal_")
    isaretli_yolu = gorsel_yaz(isaretli, ayar.cikti_dizini, on_ek="isaretli_")

    kok = ayar.veri_dizini
    return {
        "kare_indeksi": kare_indeksi,
        "kare_zamani_sn": kare_zamani_sn,
        "orijinal_gorsel": rel(orijinal_yolu, kok),
        "isaretli_gorsel": rel(isaretli_yolu, kok),
        "gradcam_gorsel": rel(gradcam_yolu, kok) if gradcam_yolu else None,
        "tahmin_sinifi": tahmin.sinif_etiketi,
        "guven": tahmin.guven,
        "desteklenmiyor": tahmin.desteklenmiyor,
        "ilk_bes": [{"sinif": a, "olasilik": o} for a, o in tahmin.ilk_bes],
        "morfoloji": {
            **morf_ozet.sozluk(),
        },
        "hucreler": [o.sozluk() for o in olcumler],
        "on_isleme": {
            **on.ozet(),
            "segmentasyon_yontemi": seg.yontem,
            "model_egitilmedi": tahmin.egitilmedi,
        },
        "risk_seviyesi": risk,
        "uyarilar": [u.sozluk() for u in uyarilar],
        "aciklama": aciklama,
        "olusturulma": dt.datetime.now(dt.timezone.utc).isoformat(),
        # ORM'e yazmak için düz alanlar
        "_orm": {
            "hucre_sayisi": morf_ozet.hucre_sayisi,
            "kaplama_orani": morf_ozet.kaplama_orani,
            "ort_hucre_alani": morf_ozet.ort_hucre_alani,
            "ort_uzunluk": morf_ozet.ort_uzunluk,
            "ort_genislik": morf_ozet.ort_genislik,
            "ort_dairesellik": morf_ozet.ort_dairesellik,
            "baskin_morfoloji": morf_ozet.baskin_morfoloji,
        },
    }
