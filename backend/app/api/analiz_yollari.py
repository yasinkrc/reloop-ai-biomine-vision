"""Analiz uç noktaları: tekli görüntü, toplu (ZIP), video, örnek veri."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.api.bagimliliklar import guncel_esikler, db
from app.config import ayarlari_al
from app.core import video as video_mod
from app.core.hat import tek_gorsel_analiz
from app.core.kayit import analiz_kaydet, analiz_sozluk
from app.core.uyari_motoru import seri_uyarilari_uret
from app.models import Numune
from app.schemas import AnalizSonuc, TopluSonuc, VideoSonuc
from app.utils.dosya import (
    benzersiz_ad,
    gorsel_mi,
    gorsel_yaz,
    video_mu,
    yukleme_kaydet,
    zip_ac,
)
from app.utils.loglama import log_al

router = APIRouter(prefix="/api/analiz", tags=["analiz"])
log = log_al(__name__)


def _boyut_kontrol(icerik: bytes) -> None:
    mb = len(icerik) / (1024 * 1024)
    sinir = ayarlari_al().maks_dosya_mb
    if mb > sinir:
        raise HTTPException(413, f"Dosya çok büyük: {mb:.1f} MB (sınır {sinir} MB)")


def _on_isleme_ayar(gurultu: bool, kontrast: bool, omnipose: bool) -> dict:
    return {
        "gurultu_azaltma": gurultu,
        "kontrast_iyilestirme": kontrast,
        "omnipose_kullan": omnipose,
    }


@router.post("/gorsel", response_model=AnalizSonuc)
async def gorsel_analiz(
    dosya: UploadFile = File(...),
    gradcam: bool = Form(True),
    gurultu_azaltma: bool = Form(True),
    kontrast_iyilestirme: bool = Form(True),
    omnipose_kullan: bool = Form(True),
    not_: str = Form("", alias="not"),
    oturum: Session = Depends(db),
    esikler: dict = Depends(guncel_esikler),
):
    """Tek bir JPG/PNG/TIFF görüntüsünü analiz eder."""
    if not gorsel_mi(dosya.filename or ""):
        raise HTTPException(400, "Desteklenmeyen görüntü biçimi. JPG, PNG veya TIFF yükleyin.")
    icerik = await dosya.read()
    _boyut_kontrol(icerik)

    ayar = ayarlari_al()
    yol = yukleme_kaydet(icerik, dosya.filename, ayar.yukleme_dizini)
    numune = Numune(ad=dosya.filename or yol.name, tur="gorsel",
                    kaynak_dosya=str(yol), not_=not_)
    oturum.add(numune)
    oturum.flush()

    try:
        sonuc = tek_gorsel_analiz(
            yol, esikler, gradcam=gradcam,
            on_isleme_ayar=_on_isleme_ayar(
                gurultu_azaltma, kontrast_iyilestirme, omnipose_kullan
            ),
        )
    except Exception as e:
        log.exception("Görsel analizi başarısız")
        raise HTTPException(500, f"Analiz sırasında hata: {e}")

    kayit = analiz_kaydet(oturum, sonuc, numune.id)
    oturum.commit()
    oturum.refresh(kayit)
    return analiz_sozluk(kayit)


@router.post("/toplu", response_model=TopluSonuc)
async def toplu_analiz(
    dosya: UploadFile = File(..., description="Görüntüler içeren ZIP dosyası"),
    gradcam: bool = Form(False),
    gurultu_azaltma: bool = Form(True),
    kontrast_iyilestirme: bool = Form(True),
    omnipose_kullan: bool = Form(True),
    oturum: Session = Depends(db),
    esikler: dict = Depends(guncel_esikler),
):
    """Bir ZIP içindeki tüm görüntüleri toplu analiz eder."""
    if not (dosya.filename or "").lower().endswith(".zip"):
        raise HTTPException(400, "Toplu analiz için .zip dosyası yükleyin.")
    icerik = await dosya.read()
    _boyut_kontrol(icerik)

    ayar = ayarlari_al()
    zip_yolu = yukleme_kaydet(icerik, dosya.filename, ayar.yukleme_dizini)
    gorseller = zip_ac(zip_yolu, ayar.yukleme_dizini / f"toplu_{benzersiz_ad('')}")
    if not gorseller:
        raise HTTPException(400, "ZIP içinde desteklenen görüntü bulunamadı.")

    numune = Numune(ad=dosya.filename or zip_yolu.name, tur="toplu",
                    kaynak_dosya=str(zip_yolu))
    oturum.add(numune)
    oturum.flush()

    sonuclar = []
    hatali = 0
    ayarlar = _on_isleme_ayar(gurultu_azaltma, kontrast_iyilestirme, omnipose_kullan)
    for g in gorseller:
        try:
            s = tek_gorsel_analiz(g, esikler, gradcam=gradcam, on_isleme_ayar=ayarlar)
            kayit = analiz_kaydet(oturum, s, numune.id)
            oturum.flush()
            sonuclar.append(analiz_sozluk(kayit))
        except Exception as e:  # tek görüntü hatası tüm partiyi düşürmesin
            hatali += 1
            log.warning("Toplu analizde görüntü atlandı (%s): %s", g.name, e)

    oturum.commit()

    ort_hucre = (
        sum(r["morfoloji"]["hucre_sayisi"] for r in sonuclar) / len(sonuclar)
        if sonuclar else 0
    )
    ozet = (
        f"{len(gorseller)} görüntüden {len(sonuclar)} tanesi başarıyla analiz edildi. "
        f"Ortalama hücre sayısı {ort_hucre:.0f}. "
        f"Kritik riskli görüntü: "
        f"{sum(1 for r in sonuclar if r['risk_seviyesi'] == 'kritik')}."
    )
    return TopluSonuc(
        numune_id=numune.id, toplam=len(gorseller), basarili=len(sonuclar),
        hatali=hatali, sonuclar=sonuclar, ozet_aciklama=ozet,
    )


@router.post("/video", response_model=VideoSonuc)
async def video_analiz(
    dosya: UploadFile = File(...),
    kare_araligi_sn: float = Form(None),
    maks_kare: int = Form(40),
    gradcam: bool = Form(False),
    oturum: Session = Depends(db),
    esikler: dict = Depends(guncel_esikler),
):
    """MP4/AVI videolarını belirli aralıklarla örnekleyip zaman serisi üretir."""
    if not video_mu(dosya.filename or ""):
        raise HTTPException(400, "Desteklenmeyen video biçimi. MP4 veya AVI yükleyin.")
    icerik = await dosya.read()
    _boyut_kontrol(icerik)

    ayar = ayarlari_al()
    aralik = kare_araligi_sn or ayar.video_kare_araligi_sn
    yol = yukleme_kaydet(icerik, dosya.filename, ayar.yukleme_dizini)

    numune = Numune(ad=dosya.filename or yol.name, tur="video", kaynak_dosya=str(yol))
    oturum.add(numune)
    oturum.flush()

    try:
        kareler = video_mod.kareleri_cikar(yol, aralik_sn=aralik, maks_kare=maks_kare)
    except Exception as e:
        raise HTTPException(400, f"Video işlenemedi: {e}")
    if not kareler:
        raise HTTPException(400, "Videodan kare çıkarılamadı.")

    kare_dizini = ayar.yukleme_dizini / f"video_{benzersiz_ad('')}"
    kare_dizini.mkdir(parents=True, exist_ok=True)

    kare_sonuclari = []
    zaman_serisi = []
    onceki_sayi = None
    for idx, zaman, rgb in kareler:
        kare_yolu = gorsel_yaz(rgb, kare_dizini, on_ek=f"kare{idx:03d}_")
        try:
            s = tek_gorsel_analiz(
                kare_yolu, esikler, gradcam=gradcam,
                onceki_hucre_sayisi=onceki_sayi,
                kare_indeksi=idx, kare_zamani_sn=zaman,
            )
        except Exception as e:
            log.warning("Video karesi atlandı (%d): %s", idx, e)
            continue
        kayit = analiz_kaydet(oturum, s, numune.id)
        oturum.flush()
        kare_sonuclari.append(analiz_sozluk(kayit))
        zaman_serisi.append({
            "kare_indeksi": idx,
            "zaman_sn": zaman,
            "hucre_sayisi": s["_orm"]["hucre_sayisi"],
            "kaplama_orani": round(s["_orm"]["kaplama_orani"], 2),
            "tahmin_sinifi": s["tahmin_sinifi"],
            "guven": s["guven"],
        })
        onceki_sayi = s["_orm"]["hucre_sayisi"]

    oturum.commit()

    seri_uyari = seri_uyarilari_uret(zaman_serisi, esikler)
    ilk = zaman_serisi[0]["hucre_sayisi"] if zaman_serisi else 0
    son = zaman_serisi[-1]["hucre_sayisi"] if zaman_serisi else 0
    ozet = (
        f"{len(zaman_serisi)} kare {aralik:.0f} sn aralıkla analiz edildi. "
        f"Hücre sayısı {ilk} → {son}. "
        + ("Seri boyunca belirgin bir aktivite kaybı sinyali var. "
           if any(u.kod == "seri_aktivite_kaybi" for u in seri_uyari)
           else "Belirgin bir seri uyarısı üretilmedi. ")
    )
    return VideoSonuc(
        numune_id=numune.id,
        kare_araligi_sn=aralik,
        kare_sayisi=len(zaman_serisi),
        zaman_serisi=zaman_serisi,
        seri_uyarilari=[u.sozluk() for u in seri_uyari],
        ozet_aciklama=ozet,
        kareler=kare_sonuclari,
    )


@router.post("/ornek", response_model=AnalizSonuc)
def ornek_analiz(
    ad: str = "cubuk_yogun",
    oturum: Session = Depends(db),
    esikler: dict = Depends(guncel_esikler),
):
    """Paketle gelen örnek görüntülerden birini analiz eder (kurulum sonrası hızlı demo)."""
    ayar = ayarlari_al()
    ornek_dizin = Path(__file__).resolve().parent.parent.parent / "ornek_veri"
    uzanti = {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp"}

    def _gorseller(kok: Path) -> list[Path]:
        return sorted(p for p in kok.rglob("*") if p.is_file() and p.suffix.lower() in uzanti)

    # Sırasıyla: depodaki vitrin görüntüsü, sınıf alt klasörü, kök dizindeki
    # hızlı-demo dosyaları, en son herhangi bir örnek.
    adaylar: list[Path] = []
    vitrin = ornek_dizin / "vitrin"
    if vitrin.is_dir():
        adaylar = [p for p in _gorseller(vitrin) if p.stem == ad] or _gorseller(vitrin)
    if not adaylar and (ornek_dizin / ad).is_dir():
        adaylar = _gorseller(ornek_dizin / ad)
    if not adaylar:
        adaylar = sorted(
            p for p in ornek_dizin.glob(f"{ad}*") if p.is_file() and p.suffix.lower() in uzanti
        )
    if not adaylar:
        adaylar = _gorseller(ornek_dizin)
    if not adaylar:
        raise HTTPException(
            404,
            "Örnek görüntü bulunamadı. `python scripts/ornek_veri_uret.py` çalıştırın.",
        )
    yol = adaylar[0]
    numune = Numune(ad=f"ornek:{yol.name}", tur="gorsel", kaynak_dosya=str(yol))
    oturum.add(numune)
    oturum.flush()
    sonuc = tek_gorsel_analiz(yol, esikler, gradcam=True)
    kayit = analiz_kaydet(oturum, sonuc, numune.id)
    oturum.commit()
    oturum.refresh(kayit)
    return analiz_sozluk(kayit)
