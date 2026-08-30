"""Sınıflandırıcının desteklediği bakteri/mikroorganizma sınıfları.

ÖNEMLİ — dürüstlük notu:
BioMine Vision'daki sınıflandırıcı, DMB AI Microscope projesinin
EfficientNetV2 + Grad-CAM yaklaşımının PyTorch ile sıfırdan yeniden
uygulanmış hâlidir. Bu depoda dağıtılan model, `scripts/model_egit.py`
ile paketteki küçük örnek veri kümesi üzerinde eğitilen bir DEMO modelidir.

Sistem YALNIZCA aşağıdaki listede yer alan, modelin gerçekten eğitildiği
sınıfları gösterir. Bu listede olmayan biyomadencilik bakterileri
(ör. Acidithiobacillus ferrooxidans, Leptospirillum) için sistem
UYDURMA tahmin yapmaz; güven düşükse sonuç
"Bilinmeyen veya desteklenmeyen bakteri" olarak döner.

Üretim kullanımı için `scripts/model_egit.py` kendi etiketli veri
kümenizle yeniden çalıştırılmalı ve `SINIFLAR` listesi güncellenmelidir.
"""
from __future__ import annotations

# Demo modelin eğitildiği sınıflar. Morfoloji temelli, biyoliç/mikrobiyoloji
# bağlamında anlamlı ve örnek veriyle temsil edilebilen genel kategoriler.
SINIFLAR: list[str] = [
    "cubuk_bakteri_yogun",      # yoğun çubuk basil kümesi
    "cubuk_bakteri_seyrek",     # seyrek çubuk basil
    "kok_bakteri_kume",         # kok (küresel) bakteri kümesi
    "kok_bakteri_zincir",       # zincir hâlinde kok
    "filamentli_organizma",     # filamentli / ipliksi yapı
    "biyofilm_matriks",         # biyofilm / EPS matriks baskın
    "karisik_kultur",           # birden çok morfoloji bir arada
    "dusuk_biyokutle",          # çok az hücre / neredeyse boş alan
]

# Kullanıcıya gösterilecek okunabilir Türkçe etiketler.
SINIF_ETIKETLERI: dict[str, str] = {
    "cubuk_bakteri_yogun": "Çubuk (basil) bakteri — yoğun koloni",
    "cubuk_bakteri_seyrek": "Çubuk (basil) bakteri — seyrek dağılım",
    "kok_bakteri_kume": "Kok (küresel) bakteri — küme",
    "kok_bakteri_zincir": "Kok (küresel) bakteri — zincir",
    "filamentli_organizma": "Filamentli / ipliksi organizma",
    "biyofilm_matriks": "Biyofilm / EPS matriks baskın",
    "karisik_kultur": "Karışık kültür (çoklu morfoloji)",
    "dusuk_biyokutle": "Düşük biyokütle / seyrek numune",
}

DESTEKLENMEYEN_ETIKET = "Bilinmeyen veya desteklenmeyen bakteri"


def etiket(sinif_anahtari: str) -> str:
    return SINIF_ETIKETLERI.get(sinif_anahtari, sinif_anahtari)
