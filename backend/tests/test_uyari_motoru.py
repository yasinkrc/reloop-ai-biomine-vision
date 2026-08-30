"""Kural motoru birim testleri."""
from __future__ import annotations

from dataclasses import dataclass

from app.config import esikleri_al
from app.core import uyari_motoru
from app.core.morfoloji import MorfolojiOzeti


@dataclass
class SahteOn:
    bulaniklik_skoru: float = 300.0
    parlaklik: float = 150.0
    orijinal_boyut: tuple = (600, 600)


@dataclass
class SahteTahmin:
    guven: float = 90.0
    desteklenmiyor: bool = False
    egitilmedi: bool = False
    sinif_etiketi: str = "Çubuk (basil) bakteri — yoğun koloni"


def _morf(**kw):
    tab = dict(
        hucre_sayisi=40, kaplama_orani=20.0, ort_hucre_alani=120.0,
        ort_uzunluk=14.0, ort_genislik=4.0, ort_dairesellik=0.4,
        baskin_morfoloji="cubuk",
        morfoloji_dagilimi={"cubuk": 38, "kuresel": 2, "filamentli": 0},
    )
    tab.update(kw)
    return MorfolojiOzeti(**tab)


ESIK = esikleri_al().model_dump()


def test_temiz_goruntu_uyari_yok():
    u = uyari_motoru.uyarilari_uret(SahteOn(), _morf(), SahteTahmin(), ESIK)
    assert u == []
    assert uyari_motoru.risk_seviyesi(u, ESIK) == "normal"


def test_bulanik_karanlik_uyarisi():
    u = uyari_motoru.uyarilari_uret(
        SahteOn(bulaniklik_skoru=10, parlaklik=12), _morf(), SahteTahmin(), ESIK
    )
    kodlar = {x.kod for x in u}
    assert "goruntu_kalitesi" in kodlar
    assert any(x.seviye == "kritik" for x in u)


def test_yetersiz_numune():
    u = uyari_motoru.uyarilari_uret(SahteOn(), _morf(hucre_sayisi=1), SahteTahmin(), ESIK)
    assert "yetersiz_numune" in {x.kod for x in u}


def test_dusuk_guven_ve_desteklenmeyen():
    u = uyari_motoru.uyarilari_uret(
        SahteOn(), _morf(), SahteTahmin(guven=40, desteklenmiyor=True), ESIK
    )
    kodlar = {x.kod for x in u}
    assert "desteklenmeyen_sinif" in kodlar


def test_asiri_yogunluk():
    u = uyari_motoru.uyarilari_uret(
        SahteOn(), _morf(kaplama_orani=80.0, hucre_sayisi=500), SahteTahmin(), ESIK
    )
    assert "asiri_yogunluk" in {x.kod for x in u}


def test_karisik_kultur():
    m = _morf(baskin_morfoloji="karisik",
             morfoloji_dagilimi={"cubuk": 20, "kuresel": 18, "filamentli": 2})
    u = uyari_motoru.uyarilari_uret(SahteOn(), m, SahteTahmin(), ESIK)
    assert "karisik_kultur" in {x.kod for x in u}


def test_aktivite_kaybi():
    u = uyari_motoru.uyarilari_uret(
        SahteOn(), _morf(hucre_sayisi=10), SahteTahmin(), ESIK,
        onceki_hucre_sayisi=100,
    )
    assert "aktivite_kaybi" in {x.kod for x in u}


def test_seri_uyarilari():
    seri = [{"hucre_sayisi": 120}, {"hucre_sayisi": 80}, {"hucre_sayisi": 20}]
    u = uyari_motoru.seri_uyarilari_uret(seri, ESIK)
    assert any(x.kod == "seri_aktivite_kaybi" for x in u)


def test_esik_degisince_davranis_degisir():
    esik = dict(ESIK)
    esik["min_hucre_sayisi"] = 100
    u = uyari_motoru.uyarilari_uret(SahteOn(), _morf(hucre_sayisi=40), SahteTahmin(), esik)
    assert "yetersiz_numune" in {x.kod for x in u}
