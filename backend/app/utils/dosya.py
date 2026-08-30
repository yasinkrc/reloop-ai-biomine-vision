"""Dosya yardımcıları: kaydetme, görüntü yazma, ZIP açma, doğrulama."""
from __future__ import annotations

import uuid
import zipfile
from pathlib import Path

import cv2
import numpy as np

from app.core.on_isleme import DESTEKLENEN_UZANTILAR
from app.utils.loglama import log_al

log = log_al(__name__)

VIDEO_UZANTILARI = {".mp4", ".avi", ".mov", ".mkv"}


def benzersiz_ad(uzanti: str) -> str:
    return f"{uuid.uuid4().hex[:16]}{uzanti}"


def yukleme_kaydet(icerik: bytes, orijinal_ad: str, hedef_dizin: Path) -> Path:
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    uzanti = Path(orijinal_ad).suffix.lower() or ".bin"
    yol = hedef_dizin / benzersiz_ad(uzanti)
    yol.write_bytes(icerik)
    return yol


def gorsel_yaz(rgb: np.ndarray, hedef_dizin: Path, on_ek: str = "") -> Path:
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    yol = hedef_dizin / f"{on_ek}{benzersiz_ad('.png')}"
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    cv2.imwrite(str(yol), bgr)
    return yol


def gorsel_mi(ad: str) -> bool:
    return Path(ad).suffix.lower() in DESTEKLENEN_UZANTILAR


def video_mu(ad: str) -> bool:
    return Path(ad).suffix.lower() in VIDEO_UZANTILARI


def zip_ac(zip_yolu: Path, hedef_dizin: Path) -> list[Path]:
    """ZIP içindeki desteklenen görüntüleri güvenli biçimde açar."""
    hedef_dizin.mkdir(parents=True, exist_ok=True)
    cikanlar: list[Path] = []
    with zipfile.ZipFile(zip_yolu) as z:
        for bilgi in z.infolist():
            if bilgi.is_dir():
                continue
            ad = Path(bilgi.filename).name
            if ad.startswith(".") or not gorsel_mi(ad):
                continue
            # Zip-slip koruması
            hedef = (hedef_dizin / benzersiz_ad(Path(ad).suffix.lower())).resolve()
            if not str(hedef).startswith(str(hedef_dizin.resolve())):
                continue
            with z.open(bilgi) as kaynak:
                hedef.write_bytes(kaynak.read())
            cikanlar.append(hedef)
    log.info("ZIP açıldı: %d görüntü (%s)", len(cikanlar), zip_yolu.name)
    return cikanlar


def rel(yol: Path | str, kok: Path) -> str:
    """API'nin döndürdüğü göreli yol (statik sunum için)."""
    try:
        return str(Path(yol).resolve().relative_to(Path(kok).resolve()))
    except ValueError:
        return str(yol)
