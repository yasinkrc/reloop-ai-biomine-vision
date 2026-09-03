"""Bakteriyel CRISPR-Cas ve genom benzerliği analizi uç noktaları."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.config import ayarlari_al
from app.core import genom as genom_mod
from app.utils.dosya import yukleme_kaydet
from app.utils.loglama import log_al

router = APIRouter(prefix="/api/genom", tags=["crispr-cas"])
log = log_al(__name__)

_ORNEK_DIZIN = Path(__file__).resolve().parent.parent.parent / "ornek_veri" / "genom"


@router.get("/durum")
def durum():
    """Hangi harici araçların kurulu olduğunu bildirir (kullanıcıya değil yönetime)."""
    return {
        "cctyper": genom_mod._arac_var("cctyper"),
        "skani": genom_mod._arac_var("skani"),
        "prodigal": genom_mod._arac_var("prodigal"),
        "referans_genom_sayisi": len(list((_ORNEK_DIZIN / "referans").glob("*.f*a")))
        if (_ORNEK_DIZIN / "referans").is_dir() else 0,
    }


@router.post("/analiz")
async def genom_analiz_yukle(
    dosya: UploadFile = File(...),
    not_: str = Form("", alias="not"),
):
    ad = dosya.filename or "genom"
    if Path(ad).suffix.lower() not in genom_mod.DESTEKLENEN:
        raise HTTPException(
            400,
            "Desteklenmeyen dosya. FASTA (.fasta/.fa/.fna), GenBank (.gb/.gbk) "
            "veya GFF (.gff/.gff3) yükleyin.",
        )
    icerik = await dosya.read()
    mb = len(icerik) / (1024 * 1024)
    if mb > ayarlari_al().maks_dosya_mb:
        raise HTTPException(413, f"Dosya çok büyük: {mb:.1f} MB")

    ayar = ayarlari_al()
    yol = yukleme_kaydet(icerik, ad, ayar.yukleme_dizini / "genom")
    try:
        return genom_mod.genom_analiz(yol, dosya_adi=ad)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        log.exception("Genom analizi başarısız")
        raise HTTPException(
            500,
            "Genom işlenirken beklenmeyen bir hata oluştu. Dosyanın geçerli bir "
            "FASTA/GenBank/GFF olduğundan emin olup yeniden deneyin.",
        )


@router.post("/ornek")
def genom_ornek():
    """Paketle gelen örnek bakteriyel genomu (gömülü CRISPR dizili) analiz eder."""
    adaylar = sorted(
        p for p in _ORNEK_DIZIN.glob("*")
        if p.is_file() and p.suffix.lower() in genom_mod.DESTEKLENEN
    )
    if not adaylar:
        raise HTTPException(
            404,
            "Örnek genom bulunamadı. `python scripts/ornek_genom_uret.py` çalıştırın.",
        )
    return genom_mod.genom_analiz(adaylar[0], dosya_adi=f"ornek:{adaylar[0].name}")
