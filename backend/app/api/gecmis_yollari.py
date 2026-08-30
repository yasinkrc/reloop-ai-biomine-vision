"""Analiz geçmişi uç noktaları."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.api.bagimliliklar import db
from app.core.kayit import analiz_sozluk
from app.models import Analiz, Numune
from app.schemas import AnalizSonuc, GecmisKaydi

router = APIRouter(prefix="/api/gecmis", tags=["gecmis"])


@router.get("", response_model=list[GecmisKaydi])
def gecmis_listele(
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
    sadece_riskli: bool = False,
    oturum: Session = Depends(db),
):
    q = oturum.query(Analiz).order_by(desc(Analiz.olusturulma))
    if sadece_riskli:
        q = q.filter(Analiz.risk_seviyesi != "normal")
    return q.offset(offset).limit(limit).all()


@router.get("/{analiz_id}", response_model=AnalizSonuc)
def gecmis_getir(analiz_id: int, oturum: Session = Depends(db)):
    kayit = oturum.get(Analiz, analiz_id)
    if not kayit:
        raise HTTPException(404, "Analiz bulunamadı")
    return analiz_sozluk(kayit)


@router.delete("/{analiz_id}", status_code=204)
def gecmis_sil(analiz_id: int, oturum: Session = Depends(db)):
    kayit = oturum.get(Analiz, analiz_id)
    if not kayit:
        raise HTTPException(404, "Analiz bulunamadı")
    oturum.delete(kayit)
    oturum.commit()


@router.get("/numune/{numune_id}", response_model=list[AnalizSonuc])
def numune_analizleri(numune_id: int, oturum: Session = Depends(db)):
    numune = oturum.get(Numune, numune_id)
    if not numune:
        raise HTTPException(404, "Numune bulunamadı")
    kayitlar = (
        oturum.query(Analiz)
        .filter(Analiz.numune_id == numune_id)
        .order_by(Analiz.kare_indeksi)
        .all()
    )
    return [analiz_sozluk(k) for k in kayitlar]
