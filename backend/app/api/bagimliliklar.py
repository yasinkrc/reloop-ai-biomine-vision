"""Ortak FastAPI bağımlılıkları."""
from __future__ import annotations

from fastapi import Depends
from sqlalchemy.orm import Session

from app.database import oturum_al
from app.models import aktif_esikler


def db(oturum: Session = Depends(oturum_al)) -> Session:
    return oturum


def guncel_esikler(oturum: Session = Depends(oturum_al)) -> dict:
    return aktif_esikler(oturum)
