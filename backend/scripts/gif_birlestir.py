#!/usr/bin/env python3
"""docs/ekran-goruntuleri/gif-kareler/*.png karelerini tek bir demo.gif'e birleştirir."""
from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image

KOK = Path(__file__).resolve().parent.parent.parent
KARE_DIZINI = KOK / "docs/ekran-goruntuleri/gif-kareler"
CIKTI = KOK / "docs/ekran-goruntuleri/demo.gif"
GENISLIK = 900
KARE_MS = 900


def main() -> None:
    kareler = sorted(KARE_DIZINI.glob("k*.png"))
    if not kareler:
        sys.exit(f"Kare bulunamadı: {KARE_DIZINI}")
    imgs = []
    for k in kareler:
        im = Image.open(k).convert("RGB")
        oran = GENISLIK / im.width
        im = im.resize((GENISLIK, int(im.height * oran)), Image.LANCZOS)
        imgs.append(im)
    imgs[0].save(
        CIKTI, save_all=True, append_images=imgs[1:], duration=KARE_MS, loop=0, optimize=True
    )
    print(f"GIF yazıldı: {CIKTI}  ({CIKTI.stat().st_size // 1024} KB, {len(imgs)} kare)")


if __name__ == "__main__":
    main()
