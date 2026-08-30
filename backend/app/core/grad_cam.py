"""Grad-CAM (Gradient-weighted Class Activation Mapping) uygulaması.

Sınıflandırıcının kararını hangi bölgelere dayandırdığını gösteren ısı
haritası üretir. DMB AI Microscope'un açıklanabilir yapay zeka yaklaşımı
referans alınmış, PyTorch ile bağımsız olarak yazılmıştır.
"""
from __future__ import annotations

import numpy as np

from app.ml.siniflandirici import Siniflandirici
from app.utils.loglama import log_al

log = log_al(__name__)


class GradCAM:
    def __init__(self, siniflandirici: Siniflandirici):
        self.s = siniflandirici
        self._aktivasyon = None
        self._gradyan = None
        self._kancalar = []

    def _kanca_tak(self):
        katman = self.s.hedef_katman

        def ileri_kanca(_modul, _giris, cikis):
            self._aktivasyon = cikis.detach()

        def geri_kanca(_modul, _giris, cikis_grad):
            self._gradyan = cikis_grad[0].detach()

        self._kancalar = [
            katman.register_forward_hook(ileri_kanca),
            katman.register_full_backward_hook(geri_kanca),
        ]

    def _kanca_kaldir(self):
        for k in self._kancalar:
            k.remove()
        self._kancalar = []

    def isi_haritasi(self, rgb: np.ndarray, sinif_indeksi: int | None = None) -> np.ndarray:
        """RGB görüntü için [0,1] aralığında ısı haritası döndürür (H,W)."""
        torch = self.s.torch
        try:
            self._kanca_tak()
            t = self.s._tensor_yap(rgb)
            t.requires_grad_(True)
            self.s.model.zero_grad(set_to_none=True)
            logitler = self.s.model(t)
            if sinif_indeksi is None:
                sinif_indeksi = int(logitler.argmax(dim=1).item())
            hedef = logitler[0, sinif_indeksi]
            hedef.backward()

            if self._aktivasyon is None or self._gradyan is None:
                raise RuntimeError("Grad-CAM kancaları veri yakalayamadı")

            agirliklar = self._gradyan.mean(dim=(2, 3), keepdim=True)   # GAP
            cam = torch.relu((agirliklar * self._aktivasyon).sum(dim=1))[0]
            cam = cam.cpu().numpy().astype(np.float32)
        except Exception as e:  # pragma: no cover - güvenli düşüş
            log.warning("Grad-CAM üretilemedi (%s). Boş ısı haritası dönülüyor.", e)
            cam = np.zeros((16, 16), dtype=np.float32)
        finally:
            self._kanca_kaldir()

        if cam.max() > cam.min():
            cam = (cam - cam.min()) / (cam.max() - cam.min())
        else:
            cam = np.zeros_like(cam)
        return cam
