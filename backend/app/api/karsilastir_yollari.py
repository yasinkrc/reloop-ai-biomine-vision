"""İki analizi karşılaştırma uç noktası."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.bagimliliklar import db
from app.core.kayit import analiz_sozluk
from app.models import Analiz
from app.schemas import KarsilastirmaIstek, KarsilastirmaSonuc

router = APIRouter(prefix="/api/karsilastir", tags=["karsilastir"])


@router.post("", response_model=KarsilastirmaSonuc)
def karsilastir(istek: KarsilastirmaIstek, oturum: Session = Depends(db)):
    a1 = oturum.get(Analiz, istek.analiz_id_1)
    a2 = oturum.get(Analiz, istek.analiz_id_2)
    if not a1 or not a2:
        raise HTTPException(404, "Karşılaştırılacak analizlerden biri bulunamadı")

    farklar = {
        "hucre_sayisi": a2.hucre_sayisi - a1.hucre_sayisi,
        "kaplama_orani": round(a2.kaplama_orani - a1.kaplama_orani, 2),
        "ort_hucre_alani": round(a2.ort_hucre_alani - a1.ort_hucre_alani, 2),
        "ort_uzunluk": round(a2.ort_uzunluk - a1.ort_uzunluk, 2),
        "ort_genislik": round(a2.ort_genislik - a1.ort_genislik, 2),
        "guven": round(a2.guven - a1.guven, 2),
    }

    yon = "arttı" if farklar["hucre_sayisi"] > 0 else (
        "azaldı" if farklar["hucre_sayisi"] < 0 else "değişmedi"
    )
    yorum_parcalari = [
        f"İkinci numunede hücre sayısı {abs(farklar['hucre_sayisi'])} birim {yon} "
        f"({a1.hucre_sayisi} → {a2.hucre_sayisi}).",
        f"Kaplama oranı farkı %{farklar['kaplama_orani']:+.1f}.",
    ]
    if a1.baskin_morfoloji != a2.baskin_morfoloji:
        yorum_parcalari.append(
            f"Baskın morfoloji değişti: {a1.baskin_morfoloji} → {a2.baskin_morfoloji} "
            f"(kültür kayması veya kontaminasyon açısından incelenmeli)."
        )
    if a1.tahmin_sinifi != a2.tahmin_sinifi:
        yorum_parcalari.append(
            f"Sınıflandırma değişti: '{a1.tahmin_sinifi}' → '{a2.tahmin_sinifi}'."
        )

    return KarsilastirmaSonuc(
        birinci=analiz_sozluk(a1),
        ikinci=analiz_sozluk(a2),
        farklar=farklar,
        yorum=" ".join(yorum_parcalari),
    )
