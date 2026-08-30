"""Pydantic şemaları — API istek/yanıt gövdeleri."""
from __future__ import annotations

import datetime as dt

from pydantic import BaseModel, Field


class Uyari(BaseModel):
    kod: str
    seviye: str  # bilgi | dikkat | kritik
    mesaj: str


class SinifOlasiligi(BaseModel):
    sinif: str
    olasilik: float = Field(description="Yüzde (0-100)")


class MorfolojiOzet(BaseModel):
    hucre_sayisi: int
    kaplama_orani: float = Field(description="Görüntü alanının yüzde kaçı hücre")
    ort_hucre_alani: float = Field(description="piksel^2")
    ort_uzunluk: float = Field(description="piksel")
    ort_genislik: float = Field(description="piksel")
    ort_dairesellik: float
    baskin_morfoloji: str  # cubuk | kuresel | filamentli | karisik | bilinmiyor
    morfoloji_dagilimi: dict[str, int]


class HucreOlcum(BaseModel):
    id: int
    alan: float
    uzunluk: float
    genislik: float
    dairesellik: float
    en_boy_orani: float
    morfoloji: str
    merkez: list[float]
    renk: list[int]


class OnIslemeOzet(BaseModel):
    gurultu_azaltma: bool
    kontrast_iyilestirme: bool
    bulaniklik_skoru: float
    parlaklik: float
    orijinal_boyut: list[int]


class AnalizSonuc(BaseModel):
    id: int | None = None
    numune_id: int | None = None
    kare_indeksi: int = 0
    kare_zamani_sn: float = 0.0

    orijinal_gorsel: str
    isaretli_gorsel: str
    gradcam_gorsel: str | None = None

    tahmin_sinifi: str
    guven: float
    desteklenmiyor: bool
    ilk_bes: list[SinifOlasiligi]

    morfoloji: MorfolojiOzet
    hucreler: list[HucreOlcum]
    on_isleme: OnIslemeOzet

    risk_seviyesi: str  # normal | dikkat | kritik
    uyarilar: list[Uyari]
    aciklama: str

    olusturulma: dt.datetime | None = None


class TopluSonuc(BaseModel):
    numune_id: int
    toplam: int
    basarili: int
    hatali: int
    sonuclar: list[AnalizSonuc]
    ozet_aciklama: str


class ZamanNoktasi(BaseModel):
    kare_indeksi: int
    zaman_sn: float
    hucre_sayisi: int
    kaplama_orani: float
    tahmin_sinifi: str
    guven: float


class VideoSonuc(BaseModel):
    numune_id: int
    kare_araligi_sn: float
    kare_sayisi: int
    zaman_serisi: list[ZamanNoktasi]
    seri_uyarilari: list[Uyari]
    ozet_aciklama: str
    kareler: list[AnalizSonuc]


class AyarGuncelle(BaseModel):
    deger: float


class AyarKaydi(BaseModel):
    anahtar: str
    deger: float
    aciklama: str

    model_config = {"from_attributes": True}


class GecmisKaydi(BaseModel):
    id: int
    numune_id: int | None
    tahmin_sinifi: str
    guven: float
    hucre_sayisi: int
    risk_seviyesi: str
    desteklenmiyor: bool
    olusturulma: dt.datetime
    isaretli_gorsel: str

    model_config = {"from_attributes": True}


class KarsilastirmaIstek(BaseModel):
    analiz_id_1: int
    analiz_id_2: int


class KarsilastirmaSonuc(BaseModel):
    birinci: AnalizSonuc
    ikinci: AnalizSonuc
    farklar: dict[str, float]
    yorum: str
