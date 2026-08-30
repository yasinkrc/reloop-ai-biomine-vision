"""ORM modelleri: analizler, numuneler, zaman serileri ve ayarlar."""
from __future__ import annotations

import datetime as dt
import json
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.config import esikleri_al
from app.database import OturumYapici, Taban


def _simdi() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


class Numune(Taban):
    """Bir numune = tek görüntü, ZIP toplu yükleme veya video kaydı."""

    __tablename__ = "numune"

    id: Mapped[int] = mapped_column(primary_key=True)
    ad: Mapped[str] = mapped_column(String(255))
    tur: Mapped[str] = mapped_column(String(20))  # gorsel | toplu | video
    kaynak_dosya: Mapped[str] = mapped_column(String(512))
    not_: Mapped[str] = mapped_column("not", Text, default="")
    olusturulma: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_simdi)

    analizler: Mapped[list["Analiz"]] = relationship(
        back_populates="numune", cascade="all, delete-orphan"
    )


class Analiz(Taban):
    """Tek bir görüntü/kare için analiz sonucu."""

    __tablename__ = "analiz"

    id: Mapped[int] = mapped_column(primary_key=True)
    numune_id: Mapped[int | None] = mapped_column(ForeignKey("numune.id"), nullable=True)
    kare_indeksi: Mapped[int] = mapped_column(Integer, default=0)
    kare_zamani_sn: Mapped[float] = mapped_column(Float, default=0.0)

    orijinal_gorsel: Mapped[str] = mapped_column(String(512), default="")
    isaretli_gorsel: Mapped[str] = mapped_column(String(512), default="")
    gradcam_gorsel: Mapped[str] = mapped_column(String(512), default="")

    hucre_sayisi: Mapped[int] = mapped_column(Integer, default=0)
    kaplama_orani: Mapped[float] = mapped_column(Float, default=0.0)
    ort_hucre_alani: Mapped[float] = mapped_column(Float, default=0.0)
    ort_uzunluk: Mapped[float] = mapped_column(Float, default=0.0)
    ort_genislik: Mapped[float] = mapped_column(Float, default=0.0)
    ort_dairesellik: Mapped[float] = mapped_column(Float, default=0.0)
    baskin_morfoloji: Mapped[str] = mapped_column(String(30), default="bilinmiyor")

    tahmin_sinifi: Mapped[str] = mapped_column(String(120), default="")
    guven: Mapped[float] = mapped_column(Float, default=0.0)
    desteklenmiyor: Mapped[bool] = mapped_column(default=False)

    risk_seviyesi: Mapped[str] = mapped_column(String(20), default="normal")  # normal|dikkat|kritik
    aciklama: Mapped[str] = mapped_column(Text, default="")

    # JSON serileştirilen alanlar
    ilk_bes_json: Mapped[str] = mapped_column(Text, default="[]")
    uyarilar_json: Mapped[str] = mapped_column(Text, default="[]")
    hucreler_json: Mapped[str] = mapped_column(Text, default="[]")
    on_isleme_json: Mapped[str] = mapped_column(Text, default="{}")

    olusturulma: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), default=_simdi)

    numune: Mapped[Numune | None] = relationship(back_populates="analizler")

    # --- yardımcı erişimciler ---
    @property
    def ilk_bes(self) -> list[dict[str, Any]]:
        return json.loads(self.ilk_bes_json or "[]")

    @property
    def uyarilar(self) -> list[dict[str, Any]]:
        return json.loads(self.uyarilar_json or "[]")

    @property
    def hucreler(self) -> list[dict[str, Any]]:
        return json.loads(self.hucreler_json or "[]")

    @property
    def on_isleme(self) -> dict[str, Any]:
        return json.loads(self.on_isleme_json or "{}")


class Ayar(Taban):
    """Yönetim ekranından değiştirilebilen anahtar/değer eşik ayarları."""

    __tablename__ = "ayar"

    anahtar: Mapped[str] = mapped_column(String(80), primary_key=True)
    deger: Mapped[str] = mapped_column(String(120))
    aciklama: Mapped[str] = mapped_column(Text, default="")
    guncellenme: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), default=_simdi, onupdate=_simdi
    )


_AYAR_ACIKLAMALARI = {
    "guven_dusuk": "Güven bunun altındaysa sonuç 'Bilinmeyen/desteklenmeyen' sayılır (%)",
    "guven_uyari": "'Sonuç güvenilir değil' uyarısı için güven eşiği (%)",
    "min_hucre_sayisi": "Numune yeterli sayılması için gereken en az hücre sayısı",
    "asiri_yogunluk_kaplama": "Aşırı yoğunluk uyarısı için görüntü kaplama oranı (%)",
    "asiri_yogunluk_mp": "Megapiksel başına hücre yoğunluğu üst sınırı",
    "baskin_morfoloji_orani": "Karışık kültür uyarısı için baskın morfoloji oranı eşiği",
    "aktivite_kaybi_dusus_orani": "Ardışık karelerde aktivite kaybı için düşüş oranı eşiği",
    "bulaniklik_esik": "Laplacian varyansı bunun altındaysa görüntü bulanık",
    "karanlik_esik": "Ortalama parlaklık bunun altındaysa görüntü karanlık",
    "kritik_uyari_sayisi": "Risk 'Kritik' sayılması için gereken uyarı sayısı",
}


def ayarlari_tohumla() -> None:
    """Ayar tablosu boşsa `Esikler` ön tanımlıları ile doldurur."""
    esik = esikleri_al()
    with OturumYapici() as oturum:
        mevcut = {a.anahtar for a in oturum.query(Ayar).all()}
        eklendi = False
        for anahtar, aciklama in _AYAR_ACIKLAMALARI.items():
            if anahtar in mevcut:
                continue
            oturum.add(
                Ayar(
                    anahtar=anahtar,
                    deger=str(getattr(esik, anahtar)),
                    aciklama=aciklama,
                )
            )
            eklendi = True
        if eklendi:
            oturum.commit()


def aktif_esikler(oturum) -> dict[str, float]:
    """Veritabanındaki güncel eşik değerlerini `Esikler` alanlarıyla birleştirir."""
    esik = esikleri_al().model_dump()
    for a in oturum.query(Ayar).all():
        try:
            esik[a.anahtar] = float(a.deger)
        except (TypeError, ValueError):
            continue
    return esik
