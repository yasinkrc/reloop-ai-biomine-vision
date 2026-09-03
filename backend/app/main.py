"""BioMine Vision — FastAPI uygulama girişi."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api import (
    analiz_yollari,
    ayar_yollari,
    disari_aktar_yollari,
    gecmis_yollari,
    genom_yollari,
    karsilastir_yollari,
    takip_yollari,
)
from app.config import ayarlari_al
from app.database import veritabanini_hazirla
from app.ml.siniflar import SINIFLAR
from app.utils.loglama import log_al

log = log_al("biomine")
ayar = ayarlari_al()


@asynccontextmanager
async def yasam_dongusu(_app: FastAPI):
    ayar.dizinleri_hazirla()
    veritabanini_hazirla()
    log.info("BioMine Vision başladı — sürüm %s", ayar.surum)
    log.info("Desteklenen sınıf sayısı: %d", len(SINIFLAR))
    yield
    log.info("BioMine Vision kapanıyor")


app = FastAPI(
    title="BioMine Vision API",
    description=(
        "Biyoliç ve mikrobiyoloji mikroskop görüntülerinin yapay zeka ile "
        "analizi: bakteri tespiti, segmentasyon (Omnipose), sayım, morfoloji, "
        "sınıflandırma, Grad-CAM ve kural tabanlı uyarılar."
    ),
    version=ayar.surum,
    lifespan=yasam_dongusu,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ayar.cors_liste,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Analiz çıktısı görüntüleri ve raporlar statik olarak sunulur.
app.mount("/veri", StaticFiles(directory=str(ayar.veri_dizini)), name="veri")

app.include_router(analiz_yollari.router)
app.include_router(gecmis_yollari.router)
app.include_router(karsilastir_yollari.router)
app.include_router(ayar_yollari.router)
app.include_router(disari_aktar_yollari.router)
app.include_router(genom_yollari.router)
app.include_router(takip_yollari.router)


@app.get("/api/saglik", tags=["sistem"])
def saglik():
    from app.core.segmentasyon import _omnipose_yukle

    omnipose_hazir = _omnipose_yukle(ayar.omnipose_model) is not None
    try:
        from app.ml.siniflandirici import siniflandiriciyi_al

        s = siniflandiriciyi_al()
        model_egitildi = not s.egitilmedi
        cihaz = str(s.cihaz)
    except Exception:
        model_egitildi = False
        cihaz = "bilinmiyor"

    return {
        "durum": "calisiyor",
        "surum": ayar.surum,
        "cihaz": cihaz,
        "omnipose_hazir": omnipose_hazir,
        "siniflandirici_egitildi": model_egitildi,
        "segmentasyon_yontemi": (
            f"omnipose:{ayar.omnipose_model}" if omnipose_hazir else "klasik-watershed"
        ),
        "desteklenen_sinif_sayisi": len(SINIFLAR),
    }


@app.get("/", tags=["sistem"])
def kok():
    return {
        "uygulama": "BioMine Vision",
        "ekip": "ReLoop AI",
        "dokuman": "/docs",
        "saglik": "/api/saglik",
    }
