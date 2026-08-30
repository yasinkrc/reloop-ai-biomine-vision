"""Analiz sonuçlarını PDF, CSV ve JSON olarak dışa aktarma."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ayarlari_al
from app.utils.dosya import benzersiz_ad
from app.utils.loglama import log_al

log = log_al(__name__)

_RISK_TR = {"normal": "Normal", "dikkat": "Dikkat", "kritik": "Kritik"}


def _analiz_satiri(a: dict[str, Any]) -> dict[str, Any]:
    morf = a.get("morfoloji", {})
    return {
        "analiz_id": a.get("id"),
        "numune_id": a.get("numune_id"),
        "kare_indeksi": a.get("kare_indeksi", 0),
        "kare_zamani_sn": a.get("kare_zamani_sn", 0.0),
        "tahmin_sinifi": a.get("tahmin_sinifi"),
        "guven_yuzde": a.get("guven"),
        "desteklenmiyor": a.get("desteklenmiyor"),
        "hucre_sayisi": morf.get("hucre_sayisi"),
        "kaplama_orani_yuzde": morf.get("kaplama_orani"),
        "ort_hucre_alani_px2": morf.get("ort_hucre_alani"),
        "ort_uzunluk_px": morf.get("ort_uzunluk"),
        "ort_genislik_px": morf.get("ort_genislik"),
        "ort_dairesellik": morf.get("ort_dairesellik"),
        "baskin_morfoloji": morf.get("baskin_morfoloji"),
        "risk_seviyesi": _RISK_TR.get(a.get("risk_seviyesi", ""), a.get("risk_seviyesi")),
        "uyari_sayisi": len(a.get("uyarilar", [])),
    }


def json_disari_aktar(analizler: list[dict], baslik: str = "biomine_rapor") -> Path:
    ayar = ayarlari_al()
    yol = ayar.rapor_dizini / f"{baslik}_{benzersiz_ad('.json')}"
    yol.write_text(
        json.dumps(analizler, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return yol


def csv_disari_aktar(analizler: list[dict], baslik: str = "biomine_rapor") -> Path:
    import pandas as pd

    ayar = ayarlari_al()
    df = pd.DataFrame([_analiz_satiri(a) for a in analizler])
    yol = ayar.rapor_dizini / f"{baslik}_{benzersiz_ad('.csv')}"
    df.to_csv(yol, index=False)
    return yol


def pdf_disari_aktar(
    analizler: list[dict], baslik: str = "BioMine Vision Analiz Raporu"
) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        Image,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    ayar = ayarlari_al()
    yol = ayar.rapor_dizini / f"biomine_rapor_{benzersiz_ad('.pdf')}"
    stiller = getSampleStyleSheet()
    ogeler = []

    ogeler.append(Paragraph(baslik, stiller["Title"]))
    ogeler.append(Paragraph(
        "ReLoop AI — Biyoliç & Mikrobiyoloji Görüntü Analizi", stiller["Normal"]
    ))
    ogeler.append(Spacer(1, 0.6 * cm))

    for i, a in enumerate(analizler, 1):
        morf = a.get("morfoloji", {})
        ogeler.append(Paragraph(
            f"Analiz #{a.get('id', i)} — {a.get('tahmin_sinifi', '-')}"
            f" (güven %{a.get('guven', 0):.0f})",
            stiller["Heading2"],
        ))

        veri = [
            ["Ölçüm", "Değer"],
            ["Hücre sayısı", morf.get("hucre_sayisi", "-")],
            ["Görüntü kaplama oranı", f"%{morf.get('kaplama_orani', 0):.1f}"],
            ["Ortalama hücre alanı", f"{morf.get('ort_hucre_alani', 0):.0f} px²"],
            ["Ortalama uzunluk", f"{morf.get('ort_uzunluk', 0):.1f} px"],
            ["Ortalama genişlik", f"{morf.get('ort_genislik', 0):.1f} px"],
            ["Baskın morfoloji", morf.get("baskin_morfoloji", "-")],
            ["Risk seviyesi", _RISK_TR.get(a.get("risk_seviyesi", ""), "-")],
        ]
        t = Table(veri, colWidths=[6 * cm, 8 * cm])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f2937")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
        ]))
        ogeler.append(t)
        ogeler.append(Spacer(1, 0.3 * cm))

        for gorsel_anahtar, etiket in (
            ("isaretli_gorsel", "İşaretlenmiş görüntü"),
            ("gradcam_gorsel", "Grad-CAM ısı haritası"),
        ):
            g = a.get(gorsel_anahtar)
            if not g:
                continue
            tam = ayar.veri_dizini / g
            if tam.exists():
                ogeler.append(Paragraph(etiket, stiller["Italic"]))
                ogeler.append(Image(str(tam), width=8 * cm, height=8 * cm, kind="proportional"))
                ogeler.append(Spacer(1, 0.2 * cm))

        if a.get("uyarilar"):
            ogeler.append(Paragraph("Uyarılar:", stiller["Heading4"]))
            for u in a["uyarilar"]:
                ogeler.append(Paragraph(
                    f"[{u['seviye'].upper()}] {u['mesaj']}", stiller["Normal"]
                ))
        ogeler.append(Paragraph(a.get("aciklama", ""), stiller["Normal"]))
        ogeler.append(Spacer(1, 0.8 * cm))

    SimpleDocTemplate(str(yol), pagesize=A4).build(ogeler)
    log.info("PDF rapor üretildi: %s", yol.name)
    return yol
