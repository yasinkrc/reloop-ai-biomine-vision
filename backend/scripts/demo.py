#!/usr/bin/env python3
"""Uçtan uca demo senaryosu (sunucu olmadan).

Adımlar:
  1. Örnek veri yoksa üretir.
  2. Tekli görüntü analizi çalıştırır.
  3. Bir ZIP oluşturup toplu analiz yapar.
  4. Sentetik kısa bir video üretip kare-kare analiz eder (zaman serisi).
  5. Sonuçları PDF / CSV / JSON olarak dışa aktarır.
  6. Özet çıktı yazar.

Kullanım:
    python scripts/demo.py
"""
from __future__ import annotations

import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))


def _ayrac(baslik: str) -> None:
    print("\n" + "=" * 64 + f"\n  {baslik}\n" + "=" * 64)


def main() -> None:
    import cv2
    import numpy as np

    from app.config import ayarlari_al, esikleri_al
    from app.core import rapor
    from app.core.hat import tek_gorsel_analiz
    from app.core.video import kareleri_cikar

    ayar = ayarlari_al()
    esik = esikleri_al().model_dump()
    ornek_dizin = KOK / "ornek_veri"

    if not list(ornek_dizin.glob("*.png")):
        _ayrac("1) Örnek veri üretiliyor")
        import subprocess
        subprocess.run(
            [sys.executable, str(KOK / "scripts" / "ornek_veri_uret.py"),
             "--sinif_basi", "12"],
            check=True, cwd=str(KOK),
        )

    ornekler = sorted(ornek_dizin.glob("*.png"))[:6]
    if not ornekler:
        raise SystemExit("Örnek görüntü bulunamadı.")

    _ayrac("2) Tekli görüntü analizi")
    sonuc = tek_gorsel_analiz(ornekler[0], esik, gradcam=True)
    print(f"  Görüntü          : {ornekler[0].name}")
    print(f"  Segmentasyon     : {sonuc['on_isleme']['segmentasyon_yontemi']}")
    print(f"  Hücre sayısı     : {sonuc['_orm']['hucre_sayisi']}")
    print(f"  Kaplama oranı    : %{sonuc['_orm']['kaplama_orani']:.1f}")
    print(f"  Baskın morfoloji : {sonuc['_orm']['baskin_morfoloji']}")
    print(f"  Tahmin           : {sonuc['tahmin_sinifi']} (güven %{sonuc['guven']:.0f})")
    print(f"  Risk             : {sonuc['risk_seviyesi']}")
    print(f"  Uyarı sayısı     : {len(sonuc['uyarilar'])}")
    for u in sonuc["uyarilar"]:
        print(f"     - [{u['seviye']}] {u['mesaj']}")
    print(f"  İşaretli görsel  : {sonuc['isaretli_gorsel']}")
    print(f"  Grad-CAM görsel  : {sonuc['gradcam_gorsel']}")

    _ayrac("3) Toplu analiz (ZIP)")
    zip_yolu = ayar.veri_dizini / "demo_toplu.zip"
    with zipfile.ZipFile(zip_yolu, "w") as z:
        for p in ornekler:
            z.write(p, arcname=p.name)
    from app.utils.dosya import zip_ac
    cikanlar = zip_ac(zip_yolu, ayar.yukleme_dizini / "demo_toplu")
    toplu_sonuclar = []
    for g in cikanlar:
        s = tek_gorsel_analiz(g, esik, gradcam=False)
        s["id"] = len(toplu_sonuclar) + 1
        toplu_sonuclar.append(s)
    ort = np.mean([s["_orm"]["hucre_sayisi"] for s in toplu_sonuclar])
    print(f"  {len(toplu_sonuclar)} görüntü analiz edildi, ortalama hücre {ort:.0f}")

    _ayrac("4) Video zaman serisi")
    video_yolu = ayar.veri_dizini / "demo_video.mp4"
    yaz = cv2.VideoWriter(
        str(video_yolu), cv2.VideoWriter_fourcc(*"mp4v"), 10, (512, 512)
    )
    # Yoğun çubuk bakteri görüntüsüyle başla, her karede temiz zeminle daha fazlasını
    # ört → tespit edilen hücre sayısı zamanla düşsün (bakteriyel aktivite kaybı senaryosu).
    yogun = sorted((ornek_dizin / "cubuk_bakteri_yogun").glob("*.png"))
    taban = cv2.imread(str(yogun[0] if yogun else ornekler[0]))
    taban = cv2.resize(taban, (512, 512))
    zemin_renk = int(taban.mean())
    for k in range(30):
        kare = taban.copy()
        sil = int(k / 29 * 480)
        if sil:
            cv2.rectangle(kare, (0, 0), (sil, 512), (zemin_renk, zemin_renk, zemin_renk), -1)
        yaz.write(kare)
    yaz.release()

    kareler = kareleri_cikar(video_yolu, aralik_sn=0.5, maks_kare=8)
    onceki = None
    seri = []
    for idx, zaman, rgb in kareler:
        kp = ayar.yukleme_dizini / f"demo_kare_{idx}.png"
        cv2.imwrite(str(kp), cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        s = tek_gorsel_analiz(kp, esik, gradcam=False, onceki_hucre_sayisi=onceki,
                              kare_indeksi=idx, kare_zamani_sn=zaman)
        seri.append((zaman, s["_orm"]["hucre_sayisi"], s["risk_seviyesi"]))
        onceki = s["_orm"]["hucre_sayisi"]
    for zaman, sayi, risk in seri:
        print(f"  t={zaman:>4.1f}s  hücre={sayi:>4}  risk={risk}")

    _ayrac("5) Rapor dışa aktarma")
    pdf = rapor.pdf_disari_aktar([sonuc])
    csv = rapor.csv_disari_aktar(toplu_sonuclar)
    js = rapor.json_disari_aktar(toplu_sonuclar)
    print(f"  PDF : {pdf}")
    print(f"  CSV : {csv}")
    print(f"  JSON: {js}")

    _ayrac("DEMO TAMAM")
    print("Tüm akış sunucu olmadan uçtan uca çalıştı. "
          "Web arayüzü için: docker compose up  ya da  scripts/kurulum.sh")


if __name__ == "__main__":
    main()
