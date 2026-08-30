#!/usr/bin/env python3
"""DEMO sınıflandırıcı eğitim betiği.

`ornek_veri/<sinif>/*.png` klasör yapısındaki görüntülerle
`efficientnet_v2_s` omurgalı sınıflandırıcıyı eğitir ve ağırlıkları
`modeller/biomine_siniflandirici.pt` dosyasına kaydeder.

ÖNEMLİ: Bu, sentetik/örnek veriyle eğitilen bir DEMO modeldir. Üretim
için kendi etiketli veri kümenizle yeniden çalıştırın ve
`app/ml/siniflar.py` içindeki `SINIFLAR` listesini güncelleyin.

Kullanım:
    python scripts/model_egit.py --veri ornek_veri --epok 8
"""
from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

KOK = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(KOK))


def main() -> None:
    import numpy as np
    import torch
    import torch.nn as nn
    from torch.utils.data import DataLoader, Dataset
    from torchvision import transforms
    from torchvision.datasets import ImageFolder

    from app.ml.siniflandirici import cihaz_sec, model_olustur
    from app.ml.siniflar import SINIFLAR

    ap = argparse.ArgumentParser()
    ap.add_argument("--veri", default="ornek_veri")
    ap.add_argument("--epok", type=int, default=8)
    ap.add_argument("--batch", type=int, default=16)
    ap.add_argument("--lr", type=float, default=3e-4)
    ap.add_argument("--cihaz", default="otomatik")
    ap.add_argument("--cikti", default=None)
    ap.add_argument("--boyut", type=int, default=224, help="Giriş görüntü kenarı (px)")
    ap.add_argument(
        "--dondur", action="store_true",
        help="Omurgayı dondur, yalnızca sınıflandırma kafasını eğit (CPU'da çok daha hızlı)",
    )
    args = ap.parse_args()

    try:
        torch.set_num_threads(max(1, (os.cpu_count() or 4)))
    except Exception:
        pass

    veri_dizini = (KOK / args.veri).resolve()
    if not veri_dizini.exists():
        raise SystemExit(
            f"Veri klasörü yok: {veri_dizini}\n"
            f"Önce: python scripts/ornek_veri_uret.py"
        )

    cihaz = cihaz_sec(args.cihaz)
    print(f"Cihaz: {cihaz}")

    egitim_tf = transforms.Compose([
        transforms.Resize((args.boyut, args.boyut)),
        transforms.RandomHorizontalFlip(),
        transforms.RandomVerticalFlip(),
        transforms.RandomRotation(20),
        transforms.ColorJitter(0.2, 0.2, 0.1),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])
    dogrulama_tf = transforms.Compose([
        transforms.Resize((args.boyut, args.boyut)),
        transforms.ToTensor(),
        transforms.Normalize((0.485, 0.456, 0.406), (0.229, 0.224, 0.225)),
    ])

    tam = ImageFolder(str(veri_dizini))
    # ImageFolder sınıf sırası alfabetiktir; kendi sıramıza eşle.
    if sorted(SINIFLAR) != sorted(tam.classes):
        print("UYARI: veri klasörü sınıfları ile SINIFLAR listesi birebir eşleşmiyor.")
    siniflar = tam.classes

    n = len(tam)
    idx = np.arange(n)
    rng = np.random.default_rng(42)
    rng.shuffle(idx)
    kesim = int(n * 0.8)
    egitim_idx, dogrulama_idx = idx[:kesim], idx[kesim:]

    class AltKume(Dataset):
        def __init__(self, taban, indeksler, tf):
            self.taban, self.indeksler, self.tf = taban, indeksler, tf

        def __len__(self):
            return len(self.indeksler)

        def __getitem__(self, i):
            yol, etiket = self.taban.samples[self.indeksler[i]]
            from PIL import Image

            g = Image.open(yol).convert("RGB")
            return self.tf(g), etiket

    egitim_dl = DataLoader(AltKume(tam, egitim_idx, egitim_tf),
                           batch_size=args.batch, shuffle=True)
    dogrulama_dl = DataLoader(AltKume(tam, dogrulama_idx, dogrulama_tf),
                              batch_size=args.batch)

    model = model_olustur(len(siniflar), on_egitimli=True).to(cihaz)

    if args.dondur:
        for ad, p in model.named_parameters():
            p.requires_grad = ad.startswith("classifier")
        egitilebilir = [p for p in model.parameters() if p.requires_grad]
        print(f"Omurga donduruldu — eğitilebilir tensör: {len(egitilebilir)}")
    else:
        egitilebilir = list(model.parameters())

    opt = torch.optim.AdamW(egitilebilir, lr=args.lr, weight_decay=1e-4)
    kayip_fn = nn.CrossEntropyLoss()

    en_iyi = 0.0
    cikti_yolu = Path(args.cikti) if args.cikti else (
        KOK.parent / "modeller" / "biomine_siniflandirici.pt"
    )
    cikti_yolu.parent.mkdir(parents=True, exist_ok=True)

    for epok in range(1, args.epok + 1):
        if args.dondur:
            model.eval()               # omurga BatchNorm istatistikleri sabit
            model.classifier.train()
        else:
            model.train()
        toplam_kayip = 0.0
        for x, y in egitim_dl:
            x, y = x.to(cihaz), y.to(cihaz)
            opt.zero_grad()
            kayip = kayip_fn(model(x), y)
            kayip.backward()
            opt.step()
            toplam_kayip += kayip.item() * x.size(0)

        model.eval()
        dogru = toplam = 0
        with torch.no_grad():
            for x, y in dogrulama_dl:
                x, y = x.to(cihaz), y.to(cihaz)
                tahmin = model(x).argmax(1)
                dogru += (tahmin == y).sum().item()
                toplam += y.size(0)
        acc = dogru / max(toplam, 1)
        print(f"Epok {epok:02d} | kayip={toplam_kayip / len(egitim_idx):.4f} | "
              f"dogrulama_dogrulugu={acc:.3f}")

        if acc >= en_iyi:
            en_iyi = acc
            torch.save(
                {"state_dict": model.state_dict(), "siniflar": siniflar,
                 "dogruluk": acc, "mimari": "efficientnet_v2_s",
                 "giris_boyutu": args.boyut, "donduruldu": args.dondur},
                cikti_yolu,
            )

    print(f"\nEn iyi doğrulama doğruluğu: {en_iyi:.3f}")
    print(f"Model kaydedildi: {cikti_yolu}")


if __name__ == "__main__":
    main()
