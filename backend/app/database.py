"""Veritabanı bağlantısı ve oturum yönetimi (SQLAlchemy)."""
from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import ayarlari_al

_ayar = ayarlari_al()

_baglanti_args = {}
if _ayar.veritabani_url.startswith("sqlite"):
    _baglanti_args = {"check_same_thread": False}

motor = create_engine(
    _ayar.veritabani_url,
    connect_args=_baglanti_args,
    pool_pre_ping=True,
    future=True,
)

OturumYapici = sessionmaker(bind=motor, autoflush=False, autocommit=False, future=True)


class Taban(DeclarativeBase):
    pass


def veritabanini_hazirla() -> None:
    """Tabloları oluşturur ve ön tanımlı ayar satırlarını ekler."""
    from app import models  # noqa: F401  (tabloların kaydı için)

    Taban.metadata.create_all(bind=motor)
    models.ayarlari_tohumla()


def oturum_al() -> Iterator[Session]:
    """FastAPI bağımlılığı olarak kullanılan veritabanı oturumu."""
    oturum = OturumYapici()
    try:
        yield oturum
    finally:
        oturum.close()
