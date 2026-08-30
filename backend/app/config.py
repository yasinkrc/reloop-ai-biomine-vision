"""Uygulama yapılandırması ve eşik değerleri.

Tüm eşik değerleri (`Esikler`) hem ortam değişkeni hem de yönetim ekranı
(`/api/ayarlar`) üzerinden değiştirilebilir. Yönetim ekranından yapılan
değişiklikler veritabanındaki `ayar` tablosunda saklanır ve uygulama
yeniden başlatıldığında da korunur.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJE_DIR = BACKEND_DIR.parent


class Esikler(BaseSettings):
    """Kural motoru ve analiz eşik değerleri.

    Bu değerler yönetim ekranından güncellenebilir; ön tanımlılar
    biyoliç numunelerinde makul başlangıç noktalarıdır.
    """

    model_config = SettingsConfigDict(env_prefix="ESIK_", extra="ignore")

    # Sınıflandırma güven eşiği (yüzde). Altında kalırsa sonuç
    # "Bilinmeyen veya desteklenmeyen bakteri" olarak işaretlenir.
    guven_dusuk: float = 55.0
    # "Sonuç güvenilir değil" uyarısının tetiklendiği eşik (yüzde).
    guven_uyari: float = 65.0

    # Görüntüde en az bu kadar hücre yoksa "numune/görüntü kalitesi yetersiz".
    min_hucre_sayisi: int = 3
    # Görüntü kaplama oranı (%) bunun üstündeyse "aşırı hücre yoğunluğu".
    asiri_yogunluk_kaplama: float = 45.0
    # Birim alan başına hücre yoğunluğu (hücre / megapiksel) üst sınırı.
    asiri_yogunluk_mp: float = 4000.0

    # Karışık kültür: baskın morfoloji oranı bunun altındaysa
    # "karışık kültür veya kontaminasyon ihtimali".
    baskin_morfoloji_orani: float = 0.60

    # Zaman serisi: ardışık iki kare arasında hücre sayısı bu oranın
    # üstünde düşerse "bakteriyel aktivite kaybı olabilir".
    aktivite_kaybi_dusus_orani: float = 0.35

    # Görüntü kalitesi: Laplacian varyansı bunun altındaysa görüntü
    # bulanık kabul edilir.
    bulaniklik_esik: float = 80.0
    # Ortalama parlaklık (0-255) bunun altındaysa görüntü karanlık kabul edilir.
    karanlik_esik: float = 35.0

    # Risk seviyesi haritalaması için: kaç uyarı "Kritik" sayılır.
    kritik_uyari_sayisi: int = 2


class Ayarlar(BaseSettings):
    """Genel uygulama ayarları."""

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_DOSYASI", str(PROJE_DIR / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    uygulama_adi: str = "BioMine Vision"
    surum: str = "0.1.0"
    hata_ayikla: bool = Field(default=False, alias="DEBUG")

    # Veritabanı: SQLite (ön tanımlı) veya PostgreSQL bağlantı adresi.
    veritabani_url: str = Field(
        default=f"sqlite:///{PROJE_DIR / 'veri' / 'biomine.db'}",
        alias="DATABASE_URL",
    )

    # Dosya yükleme kök dizini.
    veri_dizini: Path = Field(default=PROJE_DIR / "veri", alias="VERI_DIZINI")
    model_dizini: Path = Field(default=PROJE_DIR / "modeller", alias="MODEL_DIZINI")

    # CORS için izin verilen origin'ler (virgülle ayrılmış).
    cors_originler: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000", alias="CORS_ORIGINS"
    )

    # Cihaz seçimi: "otomatik" | "cpu" | "cuda".
    cihaz: str = Field(default="otomatik", alias="CIHAZ")

    # Video analizinde kaç saniyede bir kare örneklenir.
    video_kare_araligi_sn: float = Field(default=2.0, alias="VIDEO_KARE_ARALIGI")

    # Yüklenebilecek en büyük dosya boyutu (MB).
    maks_dosya_mb: int = Field(default=200, alias="MAKS_DOSYA_MB")

    # Sınıflandırıcı model dosyası (yoksa kurulum betiği indirir/oluşturur).
    siniflandirici_dosyasi: str = Field(
        default="biomine_siniflandirici.pt", alias="SINIFLANDIRICI_DOSYASI"
    )
    # Omnipose model adı (yerleşik pretrained model).
    omnipose_model: str = Field(default="bact_phase_omni", alias="OMNIPOSE_MODEL")

    @property
    def cors_liste(self) -> list[str]:
        return [o.strip() for o in self.cors_originler.split(",") if o.strip()]

    @property
    def yukleme_dizini(self) -> Path:
        return self.veri_dizini / "yuklemeler"

    @property
    def cikti_dizini(self) -> Path:
        return self.veri_dizini / "ciktilar"

    @property
    def rapor_dizini(self) -> Path:
        return self.veri_dizini / "raporlar"

    def dizinleri_hazirla(self) -> None:
        for d in (
            self.veri_dizini,
            self.model_dizini,
            self.yukleme_dizini,
            self.cikti_dizini,
            self.rapor_dizini,
        ):
            Path(d).mkdir(parents=True, exist_ok=True)


@lru_cache
def ayarlari_al() -> Ayarlar:
    a = Ayarlar()
    a.dizinleri_hazirla()
    return a


@lru_cache
def esikleri_al() -> Esikler:
    return Esikler()
