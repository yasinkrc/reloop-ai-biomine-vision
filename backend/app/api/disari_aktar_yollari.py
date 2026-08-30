"""Rapor dışa aktarma — PDF / CSV / JSON."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.bagimliliklar import db
from app.core import rapor
from app.core.kayit import analiz_sozluk
from app.models import Analiz

router = APIRouter(prefix="/api/disari-aktar", tags=["disari-aktar"])


class DisariAktarIstek(BaseModel):
    analiz_idleri: list[int]
    bicim: str = "pdf"  # pdf | csv | json


_MEDYA = {
    "pdf": "application/pdf",
    "csv": "text/csv",
    "json": "application/json",
}


@router.post("")
def disari_aktar(istek: DisariAktarIstek, oturum: Session = Depends(db)):
    if istek.bicim not in _MEDYA:
        raise HTTPException(400, "Biçim 'pdf', 'csv' veya 'json' olmalı")
    kayitlar = (
        oturum.query(Analiz).filter(Analiz.id.in_(istek.analiz_idleri)).all()
    )
    if not kayitlar:
        raise HTTPException(404, "Dışa aktarılacak analiz bulunamadı")

    analizler = [analiz_sozluk(k) for k in kayitlar]
    if istek.bicim == "pdf":
        yol = rapor.pdf_disari_aktar(analizler)
    elif istek.bicim == "csv":
        yol = rapor.csv_disari_aktar(analizler)
    else:
        yol = rapor.json_disari_aktar(analizler)

    return FileResponse(
        path=str(yol), media_type=_MEDYA[istek.bicim], filename=yol.name
    )
