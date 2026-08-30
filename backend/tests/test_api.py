"""API entegrasyon testleri (FastAPI TestClient)."""
from __future__ import annotations

import io
import zipfile

import cv2
import pytest

pytest.importorskip("torch")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

istemci = TestClient(app)


def _png_bytes(rgb) -> bytes:
    ok, buf = cv2.imencode(".png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
    assert ok
    return buf.tobytes()


def test_saglik():
    y = istemci.get("/api/saglik")
    assert y.status_code == 200
    veri = y.json()
    assert veri["durum"] == "calisiyor"
    assert "segmentasyon_yontemi" in veri
    assert veri["desteklenen_sinif_sayisi"] >= 1


def test_desteklenen_siniflar_uc_noktasi():
    y = istemci.get("/api/ayarlar/siniflar")
    assert y.status_code == 200
    assert len(y.json()["siniflar"]) >= 1


def test_gorsel_analiz_akisi(cubuk_gorsel):
    y = istemci.post(
        "/api/analiz/gorsel",
        files={"dosya": ("cubuk.png", _png_bytes(cubuk_gorsel), "image/png")},
        data={"gradcam": "true"},
    )
    assert y.status_code == 200, y.text
    veri = y.json()
    assert veri["id"] > 0
    assert veri["isaretli_gorsel"].endswith(".png")
    assert veri["morfoloji"]["hucre_sayisi"] >= 0
    assert veri["risk_seviyesi"] in {"normal", "dikkat", "kritik"}
    assert len(veri["ilk_bes"]) == 5

    # Geçmişte görünmeli
    g = istemci.get("/api/gecmis")
    assert g.status_code == 200
    assert any(k["id"] == veri["id"] for k in g.json())

    # Statik görsel sunuluyor mu
    s = istemci.get("/veri/" + veri["isaretli_gorsel"])
    assert s.status_code == 200

    return veri["id"]


def test_toplu_analiz(cubuk_gorsel):
    tampon = io.BytesIO()
    with zipfile.ZipFile(tampon, "w") as z:
        for i in range(3):
            z.writestr(f"g{i}.png", _png_bytes(cubuk_gorsel))
    tampon.seek(0)
    y = istemci.post(
        "/api/analiz/toplu",
        files={"dosya": ("parti.zip", tampon.read(), "application/zip")},
    )
    assert y.status_code == 200, y.text
    veri = y.json()
    assert veri["toplam"] == 3
    assert veri["basarili"] >= 1


def test_ayar_guncelleme():
    liste = istemci.get("/api/ayarlar").json()
    assert liste
    anahtar = "guven_uyari"
    y = istemci.put(f"/api/ayarlar/{anahtar}", json={"deger": 70.0})
    assert y.status_code == 200
    assert y.json()["deger"] == 70.0
    # geri al
    istemci.put(f"/api/ayarlar/{anahtar}", json={"deger": 65.0})


def test_disari_aktar_json(cubuk_gorsel):
    analiz_id = test_gorsel_analiz_akisi(cubuk_gorsel)
    y = istemci.post(
        "/api/disari-aktar",
        json={"analiz_idleri": [analiz_id], "bicim": "json"},
    )
    assert y.status_code == 200
    assert y.headers["content-type"].startswith("application/json")


def test_karsilastir(cubuk_gorsel):
    a = test_gorsel_analiz_akisi(cubuk_gorsel)
    b = test_gorsel_analiz_akisi(cubuk_gorsel)
    y = istemci.post("/api/karsilastir", json={"analiz_id_1": a, "analiz_id_2": b})
    assert y.status_code == 200
    assert "farklar" in y.json()
