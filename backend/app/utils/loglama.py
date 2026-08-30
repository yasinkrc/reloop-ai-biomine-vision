"""Merkezi loglama yapılandırması."""
from __future__ import annotations

import logging
import sys

_KURULDU = False


def loglamayi_kur(seviye: int = logging.INFO) -> None:
    global _KURULDU
    if _KURULDU:
        return
    bicim = "%(asctime)s | %(levelname)-7s | %(name)s | %(message)s"
    isleyici = logging.StreamHandler(sys.stdout)
    isleyici.setFormatter(logging.Formatter(bicim, datefmt="%Y-%m-%d %H:%M:%S"))
    kok = logging.getLogger()
    kok.setLevel(seviye)
    kok.handlers.clear()
    kok.addHandler(isleyici)
    # Gürültülü kütüphaneleri kıs.
    for ad in ("PIL", "matplotlib", "numba", "urllib3"):
        logging.getLogger(ad).setLevel(logging.WARNING)
    _KURULDU = True


def log_al(ad: str) -> logging.Logger:
    loglamayi_kur()
    return logging.getLogger(ad)
