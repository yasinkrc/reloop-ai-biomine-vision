"""Kural tabanlı uyarı motoru ve risk seviyesi hesabı.

Tüm eşik değerleri yönetim ekranından (`/api/ayarlar`) güncellenebilir ve
buraya `esikler` sözlüğü olarak geçirilir.
"""
from __future__ import annotations

from dataclasses import dataclass

from app.core.morfoloji import MorfolojiOzeti
from app.core.on_isleme import OnIslemeCiktisi
from app.ml.siniflandirici import TahminSonucu

# seviye: "bilgi" (yeşil), "dikkat" (sarı), "kritik" (kırmızı)


@dataclass
class UyariKaydi:
    kod: str
    seviye: str
    mesaj: str

    def sozluk(self) -> dict:
        return {"kod": self.kod, "seviye": self.seviye, "mesaj": self.mesaj}


def _mp(boyut: tuple[int, int]) -> float:
    return max(boyut[0] * boyut[1] / 1_000_000.0, 1e-6)


def uyarilari_uret(
    on: OnIslemeCiktisi,
    morf: MorfolojiOzeti,
    tahmin: TahminSonucu,
    esikler: dict,
    *,
    onceki_hucre_sayisi: int | None = None,
) -> list[UyariKaydi]:
    u: list[UyariKaydi] = []

    # 1) Görüntü kalitesi — bulanık / karanlık
    if on.bulaniklik_skoru < esikler["bulaniklik_esik"] or on.parlaklik < esikler["karanlik_esik"]:
        neden = []
        if on.bulaniklik_skoru < esikler["bulaniklik_esik"]:
            neden.append("bulanık")
        if on.parlaklik < esikler["karanlik_esik"]:
            neden.append("karanlık")
        u.append(UyariKaydi(
            "goruntu_kalitesi",
            "kritik",
            f"Görüntü {' ve '.join(neden)}. Netlik ve aydınlatmayı düzeltip görüntüyü yeniden yükleyin.",
        ))

    # 2) Bakteri bulunamadı / yetersiz numune
    if morf.hucre_sayisi < esikler["min_hucre_sayisi"]:
        u.append(UyariKaydi(
            "yetersiz_numune",
            "kritik",
            "Numune veya görüntü kalitesi yetersiz: anlamlı analiz için yeterli hücre tespit edilemedi.",
        ))

    # 3) Düşük güven
    if not tahmin.desteklenmiyor and tahmin.guven < esikler["guven_uyari"]:
        u.append(UyariKaydi(
            "dusuk_guven",
            "dikkat",
            f"Sonuç güvenilir değil: sınıflandırma güveni %{tahmin.guven:.0f}, "
            f"eşik %{esikler['guven_uyari']:.0f}.",
        ))
    if tahmin.desteklenmiyor:
        u.append(UyariKaydi(
            "desteklenmeyen_sinif",
            "dikkat",
            "Tahmin edilen yapı modelin desteklediği sınıflara güvenle eşlenemedi "
            "(Bilinmeyen veya desteklenmeyen bakteri).",
        ))

    # 4) Aşırı hücre yoğunluğu
    yogunluk_mp = morf.hucre_sayisi / _mp(on.orijinal_boyut)
    if (
        morf.kaplama_orani > esikler["asiri_yogunluk_kaplama"]
        or yogunluk_mp > esikler["asiri_yogunluk_mp"]
    ):
        u.append(UyariKaydi(
            "asiri_yogunluk",
            "dikkat",
            f"Aşırı hücre yoğunluğu analizi etkileyebilir "
            f"(kaplama %{morf.kaplama_orani:.0f}, {yogunluk_mp:.0f} hücre/MP). "
            f"Numuneyi seyreltmeyi deneyin.",
        ))

    # 5) Karışık kültür / kontaminasyon
    if morf.hucre_sayisi >= 4:
        baskin_sayi = max(morf.morfoloji_dagilimi.values())
        oran = baskin_sayi / max(sum(morf.morfoloji_dagilimi.values()), 1)
        if morf.baskin_morfoloji == "karisik" or oran < esikler["baskin_morfoloji_orani"]:
            u.append(UyariKaydi(
                "karisik_kultur",
                "dikkat",
                "Belirgin biçimde farklı morfolojiler görülüyor: "
                "karışık kültür veya kontaminasyon ihtimali.",
            ))

    # 6) Zaman serisi — aktivite kaybı
    if onceki_hucre_sayisi is not None and onceki_hucre_sayisi > 0:
        dusus = (onceki_hucre_sayisi - morf.hucre_sayisi) / onceki_hucre_sayisi
        if dusus >= esikler["aktivite_kaybi_dusus_orani"]:
            u.append(UyariKaydi(
                "aktivite_kaybi",
                "kritik",
                f"Ardışık görüntülerde hücre sayısı hızlı düşüyor "
                f"(%{dusus * 100:.0f}): bakteriyel aktivite kaybı olabilir.",
            ))

    return u


def seri_uyarilari_uret(zaman_serisi: list[dict], esikler: dict) -> list[UyariKaydi]:
    """Tüm video/zaman-sıralı seri için toplu uyarılar."""
    u: list[UyariKaydi] = []
    if len(zaman_serisi) < 2:
        return u
    ilk = zaman_serisi[0]["hucre_sayisi"]
    son = zaman_serisi[-1]["hucre_sayisi"]
    if ilk > 0 and (ilk - son) / ilk >= esikler["aktivite_kaybi_dusus_orani"]:
        u.append(UyariKaydi(
            "seri_aktivite_kaybi",
            "kritik",
            f"Seri boyunca hücre sayısı {ilk} → {son} düştü: "
            f"bakteriyel aktivite kaybı veya numune bozulması olabilir.",
        ))
    if ilk > 0 and son > ilk * 1.5:
        u.append(UyariKaydi(
            "seri_buyume",
            "bilgi",
            f"Seri boyunca hücre sayısı {ilk} → {son} arttı: aktif üreme gözleniyor.",
        ))
    return u


def risk_seviyesi(uyarilar: list[UyariKaydi], esikler: dict) -> str:
    kritik = sum(1 for x in uyarilar if x.seviye == "kritik")
    dikkat = sum(1 for x in uyarilar if x.seviye == "dikkat")
    if kritik >= 1 and kritik >= int(esikler["kritik_uyari_sayisi"]):
        return "kritik"
    if kritik >= 1 or dikkat >= 2:
        return "dikkat"
    if dikkat == 1:
        return "dikkat"
    return "normal"


RISK_ETIKET = {"normal": "Normal", "dikkat": "Dikkat", "kritik": "Kritik"}


def aciklama_uret(
    morf: MorfolojiOzeti,
    tahmin: TahminSonucu,
    uyarilar: list[UyariKaydi],
    seg_yontem: str,
    risk: str,
) -> str:
    """Sade Türkçe özet açıklama."""
    p = []
    if tahmin.desteklenmiyor:
        p.append(
            "Modelin desteklediği sınıflara güvenle eşlenemedi; sonuç "
            "\"Bilinmeyen veya desteklenmeyen bakteri\" olarak verildi."
        )
    else:
        p.append(
            f"Tam görüntü sınıflandırması: {tahmin.sinif_etiketi} "
            f"(güven %{tahmin.guven:.0f})."
        )
    p.append(
        f"Segmentasyon ({seg_yontem}) ile {morf.hucre_sayisi} hücre ayrıldı; "
        f"görüntünün yaklaşık %{morf.kaplama_orani:.0f}'i hücrelerle kaplı. "
        f"Ortalama hücre alanı {morf.ort_hucre_alani:.0f} piksel², "
        f"uzunluk {morf.ort_uzunluk:.1f} piksel, genişlik {morf.ort_genislik:.1f} piksel."
    )
    morf_ad = {
        "cubuk": "çubuk (basil)", "kuresel": "küresel (kok)",
        "filamentli": "filamentli", "karisik": "karışık", "bilinmiyor": "belirsiz",
    }.get(morf.baskin_morfoloji, morf.baskin_morfoloji)
    p.append(f"Baskın morfoloji: {morf_ad}.")

    if uyarilar:
        p.append("Uyarılar: " + " ".join(f"• {x.mesaj}" for x in uyarilar))
    else:
        p.append("Belirgin bir uyarı üretilmedi.")
    p.append(f"Genel risk seviyesi: {RISK_ETIKET[risk]}.")
    return " ".join(p)
