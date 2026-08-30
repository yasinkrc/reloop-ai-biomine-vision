"""Ortak test fikstürleri."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

import numpy as np
import pytest

# Testler izole bir veri dizini ve SQLite dosyası kullanır.
_GECICI = Path(tempfile.mkdtemp(prefix="biomine_test_"))
os.environ.setdefault("VERI_DIZINI", str(_GECICI / "veri"))
os.environ.setdefault("MODEL_DIZINI", str(_GECICI / "modeller"))
os.environ.setdefault("DATABASE_URL", f"sqlite:///{_GECICI / 'test.db'}")
os.environ.setdefault("CIHAZ", "cpu")


@pytest.fixture(scope="session")
def gecici_kok() -> Path:
    return _GECICI


@pytest.fixture(scope="session", autouse=True)
def _veritabani_hazir():
    """Tüm testler için tabloları ve ön tanımlı ayarları oluşturur."""
    from app.database import veritabanini_hazirla

    veritabanini_hazirla()
    yield


def _cizgi(img, p1, p2, kalinlik=5, koyu=80):
    import cv2

    cv2.line(img, p1, p2, (koyu, koyu, koyu), kalinlik, cv2.LINE_AA)


@pytest.fixture
def cubuk_gorsel() -> np.ndarray:
    """Sentetik çubuk bakteri görüntüsü (net, aydınlık)."""
    import cv2

    img = np.full((320, 320, 3), 190, np.uint8)
    rng = np.random.default_rng(0)
    for _ in range(40):
        x, y = rng.integers(20, 300, 2)
        ang = rng.uniform(0, np.pi)
        dx, dy = int(np.cos(ang) * 14), int(np.sin(ang) * 14)
        _cizgi(img, (int(x - dx), int(y - dy)), (int(x + dx), int(y + dy)))
    return cv2.GaussianBlur(img, (3, 3), 0)


@pytest.fixture
def bos_gorsel() -> np.ndarray:
    """Neredeyse boş, hücresiz görüntü."""
    return np.full((256, 256, 3), 195, np.uint8)


@pytest.fixture
def karanlik_bulanik_gorsel() -> np.ndarray:
    import cv2

    img = np.full((256, 256, 3), 18, np.uint8)
    return cv2.GaussianBlur(img, (21, 21), 0)


@pytest.fixture
def gorsel_dosya(cubuk_gorsel, tmp_path) -> Path:
    import cv2

    yol = tmp_path / "cubuk.png"
    cv2.imwrite(str(yol), cv2.cvtColor(cubuk_gorsel, cv2.COLOR_RGB2BGR))
    return yol
