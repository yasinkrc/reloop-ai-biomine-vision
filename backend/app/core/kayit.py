"""Analiz sözlüğü ↔ ORM kaydı dönüşümleri."""
from __future__ import annotations

import json
from typing import Any

from sqlalchemy.orm import Session

from app.models import Analiz


def analiz_kaydet(oturum: Session, sonuc: dict[str, Any], numune_id: int | None) -> Analiz:
    orm = sonuc.get("_orm", {})
    kayit = Analiz(
        numune_id=numune_id,
        kare_indeksi=sonuc.get("kare_indeksi", 0),
        kare_zamani_sn=sonuc.get("kare_zamani_sn", 0.0),
        orijinal_gorsel=sonuc.get("orijinal_gorsel", ""),
        isaretli_gorsel=sonuc.get("isaretli_gorsel", ""),
        gradcam_gorsel=sonuc.get("gradcam_gorsel") or "",
        hucre_sayisi=orm.get("hucre_sayisi", 0),
        kaplama_orani=orm.get("kaplama_orani", 0.0),
        ort_hucre_alani=orm.get("ort_hucre_alani", 0.0),
        ort_uzunluk=orm.get("ort_uzunluk", 0.0),
        ort_genislik=orm.get("ort_genislik", 0.0),
        ort_dairesellik=orm.get("ort_dairesellik", 0.0),
        baskin_morfoloji=orm.get("baskin_morfoloji", "bilinmiyor"),
        tahmin_sinifi=sonuc.get("tahmin_sinifi", ""),
        guven=sonuc.get("guven", 0.0),
        desteklenmiyor=bool(sonuc.get("desteklenmiyor", False)),
        risk_seviyesi=sonuc.get("risk_seviyesi", "normal"),
        aciklama=sonuc.get("aciklama", ""),
        ilk_bes_json=json.dumps(sonuc.get("ilk_bes", []), ensure_ascii=False),
        uyarilar_json=json.dumps(sonuc.get("uyarilar", []), ensure_ascii=False),
        hucreler_json=json.dumps(sonuc.get("hucreler", []), ensure_ascii=False),
        on_isleme_json=json.dumps(sonuc.get("on_isleme", {}), ensure_ascii=False),
    )
    oturum.add(kayit)
    oturum.flush()
    return kayit


def analiz_sozluk(kayit: Analiz) -> dict[str, Any]:
    return {
        "id": kayit.id,
        "numune_id": kayit.numune_id,
        "kare_indeksi": kayit.kare_indeksi,
        "kare_zamani_sn": kayit.kare_zamani_sn,
        "orijinal_gorsel": kayit.orijinal_gorsel,
        "isaretli_gorsel": kayit.isaretli_gorsel,
        "gradcam_gorsel": kayit.gradcam_gorsel or None,
        "tahmin_sinifi": kayit.tahmin_sinifi,
        "guven": kayit.guven,
        "desteklenmiyor": kayit.desteklenmiyor,
        "ilk_bes": kayit.ilk_bes,
        "morfoloji": {
            "hucre_sayisi": kayit.hucre_sayisi,
            "kaplama_orani": kayit.kaplama_orani,
            "ort_hucre_alani": kayit.ort_hucre_alani,
            "ort_uzunluk": kayit.ort_uzunluk,
            "ort_genislik": kayit.ort_genislik,
            "ort_dairesellik": kayit.ort_dairesellik,
            "baskin_morfoloji": kayit.baskin_morfoloji,
            "morfoloji_dagilimi": _dagilim(kayit.hucreler),
        },
        "hucreler": kayit.hucreler,
        "on_isleme": kayit.on_isleme,
        "risk_seviyesi": kayit.risk_seviyesi,
        "uyarilar": kayit.uyarilar,
        "aciklama": kayit.aciklama,
        "olusturulma": kayit.olusturulma,
    }


def _dagilim(hucreler: list[dict]) -> dict[str, int]:
    d = {"cubuk": 0, "kuresel": 0, "filamentli": 0}
    for h in hucreler:
        m = h.get("morfoloji")
        if m in d:
            d[m] += 1
    return d
