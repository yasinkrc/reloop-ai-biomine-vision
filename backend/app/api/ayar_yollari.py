"""Yönetim ekranı — eşik değerlerinin okunması ve güncellenmesi."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.bagimliliklar import db
from app.ml.siniflar import SINIF_ETIKETLERI, SINIFLAR
from app.models import Ayar
from app.schemas import AyarGuncelle, AyarKaydi

router = APIRouter(prefix="/api/ayarlar", tags=["ayarlar"])


@router.get("", response_model=list[AyarKaydi])
def ayarlari_listele(oturum: Session = Depends(db)):
    kayitlar = oturum.query(Ayar).order_by(Ayar.anahtar).all()
    return [
        AyarKaydi(anahtar=k.anahtar, deger=float(k.deger), aciklama=k.aciklama)
        for k in kayitlar
    ]


@router.put("/{anahtar}", response_model=AyarKaydi)
def ayar_guncelle(anahtar: str, govde: AyarGuncelle, oturum: Session = Depends(db)):
    kayit = oturum.get(Ayar, anahtar)
    if not kayit:
        raise HTTPException(404, f"Bilinmeyen ayar anahtarı: {anahtar}")
    if govde.deger < 0:
        raise HTTPException(400, "Eşik değeri negatif olamaz")
    kayit.deger = str(govde.deger)
    oturum.commit()
    oturum.refresh(kayit)
    return AyarKaydi(anahtar=kayit.anahtar, deger=float(kayit.deger), aciklama=kayit.aciklama)


@router.get("/siniflar")
def desteklenen_siniflar():
    """Modelin gerçekten desteklediği sınıf listesi (şeffaflık için)."""
    return {
        "siniflar": [
            {"anahtar": s, "etiket": SINIF_ETIKETLERI.get(s, s)} for s in SINIFLAR
        ],
        "not": (
            "Bu listede olmayan bakteriler için sistem uydurma tahmin yapmaz; "
            "güven düşükse sonuç 'Bilinmeyen veya desteklenmeyen bakteri' olur."
        ),
    }
