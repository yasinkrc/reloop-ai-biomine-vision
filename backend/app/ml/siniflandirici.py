"""PyTorch tabanlı tam görüntü sınıflandırıcı.

Mimari: torchvision `efficientnet_v2_s` omurgası + numune sınıflarına göre
yeniden boyutlandırılmış sınıflandırma kafası. DMB AI Microscope'un
EfficientNetV2 + Grad-CAM yaklaşımı referans alınmıştır (kod kopyalanmamış,
PyTorch ile yeniden yazılmıştır).

Model dosyası (`modeller/biomine_siniflandirici.pt`) yoksa sistem:
  1) ImageNet ön eğitimli omurga + rastgele başlatılmış kafa ile çalışır,
  2) her tahmini `egitilmedi=True` bayrağıyla işaretler,
  3) güven düşük olduğunda "Bilinmeyen veya desteklenmeyen bakteri" döner.
`scripts/model_egit.py` çalıştırıldığında gerçek ağırlıklar üretilir.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from app.config import ayarlari_al
from app.ml.siniflar import DESTEKLENMEYEN_ETIKET, SINIFLAR, etiket
from app.utils.loglama import log_al

log = log_al(__name__)

_GIRIS_BOYUTU = 288
_ORT = (0.485, 0.456, 0.406)
_STD = (0.229, 0.224, 0.225)

_kilit = threading.Lock()
_ornek: "Siniflandirici | None" = None


@dataclass
class TahminSonucu:
    sinif_anahtari: str
    sinif_etiketi: str
    guven: float                       # yüzde (0-100)
    ilk_bes: list[tuple[str, float]]   # (etiket, yüzde)
    desteklenmiyor: bool
    egitilmedi: bool
    logit_vektoru: np.ndarray = field(repr=False, default=None)


def cihaz_sec(tercih: str = "otomatik"):
    import torch

    if tercih == "cpu":
        return torch.device("cpu")
    if tercih == "cuda":
        return torch.device("cuda" if torch.cuda.is_available() else "cpu")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def model_olustur(sinif_sayisi: int, on_egitimli: bool = True):
    import torch.nn as nn
    from torchvision.models import EfficientNet_V2_S_Weights, efficientnet_v2_s

    agirliklar = EfficientNet_V2_S_Weights.IMAGENET1K_V1 if on_egitimli else None
    model = efficientnet_v2_s(weights=agirliklar)
    ic_ozellik = model.classifier[1].in_features
    model.classifier = nn.Sequential(
        nn.Dropout(p=0.3, inplace=True),
        nn.Linear(ic_ozellik, sinif_sayisi),
    )
    return model


class Siniflandirici:
    def __init__(self, model_yolu: str | Path | None = None, cihaz: str = "otomatik"):
        import torch

        self.torch = torch
        self.cihaz = cihaz_sec(cihaz)
        self.siniflar = list(SINIFLAR)
        self.model = model_olustur(len(self.siniflar), on_egitimli=True)
        self.egitilmedi = True
        self.giris_boyutu = _GIRIS_BOYUTU
        self.model_yolu = Path(model_yolu) if model_yolu else None

        if self.model_yolu and self.model_yolu.exists():
            try:
                # Dosya bu proje tarafından üretilir; güvenilir kabul edilir.
                durum = torch.load(self.model_yolu, map_location="cpu", weights_only=False)
                if isinstance(durum, dict) and "state_dict" in durum:
                    if durum.get("siniflar"):
                        self.siniflar = list(durum["siniflar"])
                        self.model = model_olustur(len(self.siniflar), on_egitimli=False)
                    if durum.get("giris_boyutu"):
                        self.giris_boyutu = int(durum["giris_boyutu"])
                    self.model.load_state_dict(durum["state_dict"])
                else:
                    self.model.load_state_dict(durum)
                self.egitilmedi = False
                log.info("Sınıflandırıcı ağırlıkları yüklendi: %s", self.model_yolu)
            except Exception as e:
                log.warning("Model dosyası yüklenemedi (%s). Eğitilmemiş model kullanılıyor.", e)
        else:
            log.warning(
                "Sınıflandırıcı ağırlık dosyası yok. Eğitilmemiş model ile çalışılıyor "
                "(tahminler 'egitilmedi' olarak işaretlenir). scripts/model_egit.py çalıştırın."
            )

        self.model.to(self.cihaz).eval()
        self.hedef_katman = self.model.features[-1]  # Grad-CAM için son evrişim bloğu

    # --- ön işleme ---
    def _tensor_yap(self, rgb: np.ndarray):
        import cv2
        import torch

        boyut = getattr(self, "giris_boyutu", _GIRIS_BOYUTU)
        g = cv2.resize(rgb, (boyut, boyut), interpolation=cv2.INTER_AREA)
        g = g.astype(np.float32) / 255.0
        g = (g - np.array(_ORT, dtype=np.float32)) / np.array(_STD, dtype=np.float32)
        t = torch.from_numpy(g.transpose(2, 0, 1)).unsqueeze(0).contiguous()
        return t.to(self.cihaz)

    # --- çıkarım ---
    def tahmin_et(self, rgb: np.ndarray, guven_dusuk_esik: float = 55.0) -> TahminSonucu:
        import torch

        t = self._tensor_yap(rgb)
        with torch.no_grad():
            logitler = self.model(t)
            olasiliklar = torch.softmax(logitler, dim=1)[0].cpu().numpy()

        sirali = np.argsort(olasiliklar)[::-1]
        ilk_bes = [
            (etiket(self.siniflar[i]), float(olasiliklar[i] * 100.0))
            for i in sirali[:5]
        ]
        en_iyi = int(sirali[0])
        guven = float(olasiliklar[en_iyi] * 100.0)
        desteklenmiyor = self.egitilmedi or guven < guven_dusuk_esik

        return TahminSonucu(
            sinif_anahtari=self.siniflar[en_iyi],
            sinif_etiketi=DESTEKLENMEYEN_ETIKET if desteklenmiyor else etiket(self.siniflar[en_iyi]),
            guven=round(guven, 2),
            ilk_bes=[(a, round(o, 2)) for a, o in ilk_bes],
            desteklenmiyor=desteklenmiyor,
            egitilmedi=self.egitilmedi,
            logit_vektoru=logitler.detach().cpu().numpy()[0],
        )


def siniflandiriciyi_al() -> Siniflandirici:
    """Süreç genelinde tek örnek (lazy singleton)."""
    global _ornek
    if _ornek is None:
        with _kilit:
            if _ornek is None:
                ayar = ayarlari_al()
                _ornek = Siniflandirici(
                    model_yolu=ayar.model_dizini / ayar.siniflandirici_dosyasi,
                    cihaz=ayar.cihaz,
                )
    return _ornek
