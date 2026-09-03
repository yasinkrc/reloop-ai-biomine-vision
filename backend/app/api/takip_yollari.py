"""Hücre takibi (cell tracking) uç noktaları."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import ayarlari_al
from app.core import takip as takip_mod
from app.utils.dosya import yukleme_kaydet
from app.utils.loglama import log_al

router = APIRouter(prefix="/api/takip", tags=["hucre-takibi"])
log = log_al(__name__)

_ORNEK = Path(__file__).resolve().parent.parent.parent / "ornek_veri" / "takip"
_UZANTILAR = {".mp4", ".avi", ".mov", ".mkv", ".tif", ".tiff", ".zip"}


@router.get("/durum")
def durum():
    var = False
    try:
        import trackastra  # noqa: F401

        var = True
    except Exception:
        var = False
    return {"trackastra": var}


@router.post("/analiz")
async def takip_analiz_yukle(
    dosya: UploadFile = File(...),
    kare_araligi_sn: float = Form(1.0),
):
    ad = dosya.filename or "zaman_serisi"
    if Path(ad).suffix.lower() not in _UZANTILAR:
        raise HTTPException(
            400,
            "Desteklenmeyen dosya. MP4/AVI video, çok sayfalı TIFF veya kare "
            "görüntüleri içeren ZIP yükleyin.",
        )
    icerik = await dosya.read()
    mb = len(icerik) / (1024 * 1024)
    if mb > ayarlari_al().maks_dosya_mb:
        raise HTTPException(413, f"Dosya çok büyük: {mb:.1f} MB")

    ayar = ayarlari_al()
    yol = yukleme_kaydet(icerik, ad, ayar.yukleme_dizini / "takip")
    try:
        return takip_mod.takip_analiz(
            yol, aralik_sn=max(0.1, kare_araligi_sn), dosya_adi=ad
        )
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        log.exception("Takip analizi başarısız")
        raise HTTPException(
            500,
            "Zaman serisi işlenirken beklenmeyen bir hata oluştu. Dosyayı kontrol "
            "edip yeniden deneyin.",
        )


@router.post("/ornek")
def takip_ornek():
    # Ardışık kareler içeren ZIP tercih edilir (eşleme çok daha güvenilir).
    zip_yol = _ORNEK / "takip_demo_kareler.zip"
    if zip_yol.exists():
        return takip_mod.takip_analiz(zip_yol, aralik_sn=0.5,
                                      dosya_adi=f"ornek:{zip_yol.name}")
    adaylar = sorted(
        p for p in _ORNEK.glob("*") if p.is_file() and p.suffix.lower() in _UZANTILAR
    )
    if not adaylar:
        raise HTTPException(
            404,
            "Örnek zaman serisi bulunamadı. `python scripts/ornek_takip_uret.py` çalıştırın.",
        )
    return takip_mod.takip_analiz(adaylar[0], aralik_sn=0.5,
                                  dosya_adi=f"ornek:{adaylar[0].name}")
