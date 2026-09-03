"""Bakteriyel CRISPR-Cas ve karşılaştırmalı genom analizi uç noktaları."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile

from app.config import ayarlari_al
from app.core import genom as genom_mod
from app.utils.dosya import yukleme_kaydet
from app.utils.loglama import log_al

router = APIRouter(prefix="/api/genom", tags=["crispr-cas"])
log = log_al(__name__)

_ORNEK_DIZIN = Path(__file__).resolve().parent.parent.parent / "ornek_veri" / "genom"


@router.get("/durum")
def durum():
    return {
        "cctyper": genom_mod._arac_var("cctyper"),
        "skani": genom_mod._arac_var("skani"),
        "prodigal": genom_mod._arac_var("prodigal"),
        "mmseqs": genom_mod._arac_var("mmseqs"),
        "referans_genom_sayisi": len(list((_ORNEK_DIZIN / "referans").glob("*.f*a")))
        if (_ORNEK_DIZIN / "referans").is_dir() else 0,
    }


@router.post("/analiz")
async def genom_analiz_yukle(dosyalar: list[UploadFile] = File(...)):
    if not dosyalar:
        raise HTTPException(400, "En az bir genom dosyası yükleyin.")
    if len(dosyalar) > 8:
        raise HTTPException(400, "En fazla 8 genom karşılaştırılabilir.")

    ayar = ayarlari_al()
    yollar: list[Path] = []
    for d in dosyalar:
        ad = d.filename or "genom"
        if Path(ad).suffix.lower() not in genom_mod.DESTEKLENEN:
            raise HTTPException(
                400,
                f"Desteklenmeyen dosya: {ad}. FASTA (.fasta/.fa/.fna), GenBank "
                "(.gb/.gbk) veya GFF (.gff/.gff3) yükleyin.",
            )
        icerik = await d.read()
        mb = len(icerik) / (1024 * 1024)
        if mb > ayar.maks_dosya_mb:
            raise HTTPException(413, f"Dosya çok büyük: {ad} ({mb:.1f} MB)")
        yollar.append(yukleme_kaydet(icerik, ad, ayar.yukleme_dizini / "genom"))

    try:
        return genom_mod.genom_analiz(yollar)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception:
        log.exception("Genom analizi başarısız")
        raise HTTPException(
            500,
            "Genom işlenirken beklenmeyen bir hata oluştu. Dosyaların geçerli "
            "FASTA/GenBank/GFF olduğundan emin olup yeniden deneyin.",
        )


@router.post("/ornek")
def genom_ornek():
    """Paketle gelen 4 Yersinia faj genomunu karşılaştırmalı analiz eder
    (pyGenomeViz sinteni figürü — repo örneğinin aynısı)."""
    faj = sorted((_ORNEK_DIZIN / "faj").glob("*.gb*"))
    if len(faj) < 2:
        raise HTTPException(
            404,
            "Örnek faj genomları bulunamadı. `python scripts/ornek_genom_uret.py` çalıştırın.",
        )
    return genom_mod.genom_analiz(list(faj), dosya_adi="Örnek: 4 Yersinia faj karşılaştırması")


@router.post("/ornek-crispr")
def genom_ornek_crispr():
    """Paketle gelen sentetik, gömülü CRISPR dizili tek genomu analiz eder."""
    adaylar = sorted(
        p for p in _ORNEK_DIZIN.glob("*")
        if p.is_file() and p.suffix.lower() in genom_mod.DESTEKLENEN
    )
    if not adaylar:
        raise HTTPException(
            404,
            "Örnek CRISPR genomu bulunamadı. `python scripts/ornek_genom_uret.py` çalıştırın.",
        )
    return genom_mod.genom_analiz(adaylar[0], dosya_adi=f"Örnek: {adaylar[0].name}")
