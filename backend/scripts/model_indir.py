#!/usr/bin/env python3
"""Modelleri güvenli biçimde hazırlar.

1) Sınıflandırıcı ağırlığı (`modeller/biomine_siniflandirici.pt`):
   - Ortam değişkeni `SINIFLANDIRICI_URL` tanımlıysa oradan indirilir
     (yalnızca https, SHA256 doğrulaması opsiyonel `SINIFLANDIRICI_SHA256`).
   - Yoksa ve `--egit` verilmişse örnek veri üretilip DEMO model eğitilir.
2) Omnipose pretrained modeli: kuruluysa ilk kullanımda otomatik iner;
   bu betik modeli bir kez yükleyerek indirmeyi tetikler.

Kullanım:
    python scripts/model_indir.py --egit
"""
from __future__ import annotations

import argparse
import hashlib
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))


def _indir(url: str, hedef: Path, sha256: str | None) -> None:
    if not url.lower().startswith("https://"):
        raise SystemExit("Güvenlik: yalnızca https indirmelerine izin verilir.")
    print(f"İndiriliyor: {url}")
    hedef.parent.mkdir(parents=True, exist_ok=True)
    gecici = hedef.with_suffix(hedef.suffix + ".indiriliyor")
    with urllib.request.urlopen(url, timeout=60) as yanit, open(gecici, "wb") as f:
        f.write(yanit.read())
    if sha256:
        ozet = hashlib.sha256(gecici.read_bytes()).hexdigest()
        if ozet.lower() != sha256.lower():
            gecici.unlink(missing_ok=True)
            raise SystemExit(f"SHA256 uyuşmuyor: beklenen {sha256}, gelen {ozet}")
    gecici.rename(hedef)
    print(f"Kaydedildi: {hedef}")


def siniflandiriciyi_hazirla(egit: bool) -> None:
    from app.config import ayarlari_al

    ayar = ayarlari_al()
    hedef = ayar.model_dizini / ayar.siniflandirici_dosyasi
    if hedef.exists():
        print(f"Sınıflandırıcı zaten var: {hedef}")
        return

    url = os.getenv("SINIFLANDIRICI_URL", "").strip()
    if url:
        _indir(url, hedef, os.getenv("SINIFLANDIRICI_SHA256"))
        return

    if not egit:
        print(
            "Sınıflandırıcı ağırlığı yok. `--egit` ile DEMO model eğiteb(ilir) "
            "veya SINIFLANDIRICI_URL tanımlayabilirsiniz. Sistem bu hâliyle "
            "eğitilmemiş model ile çalışır (tahminler 'egitilmedi' işaretli)."
        )
        return

    print("DEMO model eğitiliyor (örnek veri üretiliyor)...")
    subprocess.run(
        [sys.executable, str(KOK / "scripts" / "ornek_veri_uret.py"),
         "--sinif_basi", "36"],
        check=True, cwd=str(KOK),
    )
    subprocess.run(
        [sys.executable, str(KOK / "scripts" / "model_egit.py"),
         "--epok", "6", "--dondur", "--boyut", "224", "--cikti", str(hedef)],
        check=True, cwd=str(KOK),
    )


def omniposu_isit() -> None:
    try:
        from app.config import ayarlari_al
        from app.core.segmentasyon import _omnipose_yukle

        m = _omnipose_yukle(ayarlari_al().omnipose_model)
        print("Omnipose modeli hazır." if m else
              "Omnipose kurulu değil — sistem klasik watershed segmentasyonuna düşecek.")
    except Exception as e:
        print(f"Omnipose ısıtma atlandı: {e}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--egit", action="store_true",
                    help="Ağırlık yoksa örnek veriyle DEMO model eğit")
    ap.add_argument("--omnipose", action="store_true", help="Omnipose modelini indir/ısıt")
    args = ap.parse_args()

    siniflandiriciyi_hazirla(args.egit)
    if args.omnipose:
        omniposu_isit()
    print("Model hazırlığı tamam.")


if __name__ == "__main__":
    main()
