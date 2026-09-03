"""CRISPR-Cas / genom analizi testleri."""
from __future__ import annotations

import random
from pathlib import Path

import pytest

pytest.importorskip("Bio")
pytest.importorskip("pygenomeviz")

from app.core import genom as G  # noqa: E402

TEKRAR = "GTGTTCCCCGCGCCAGCGGGGATAAACCG"  # 28 bp kanonik tekrar


def _crispr_fasta(tmp_path: Path, aralayici: int = 12) -> Path:
    rng = random.Random(1)
    baz = "ACGT"

    def rs(n):
        return "".join(rng.choice(baz) for _ in range(n))

    parts = [rs(2000)]
    for _ in range(aralayici):
        parts.append(TEKRAR)
        parts.append(rs(rng.randint(30, 33)))
    parts.append(TEKRAR)
    parts.append(rs(2000))
    dizi = "".join(parts)
    yol = tmp_path / "crispr.fasta"
    yol.write_text(">test_kontig kanonik CRISPR\n" + dizi + "\n")
    return yol


def test_crispr_bul_crt_diziyi_bulur(tmp_path):
    yol = _crispr_fasta(tmp_path, aralayici=14)
    (kid, seq), = G.dizi_oku(yol)
    diziler = G.crispr_bul_crt(kid, seq)
    assert diziler, "CRISPR dizisi bulunamadı"
    en_buyuk = max(diziler, key=lambda d: d.aralayici_sayisi)
    assert en_buyuk.aralayici_sayisi >= 10
    assert G.MIN_TEKRAR <= en_buyuk.tekrar_uzunlugu <= G.MAKS_TEKRAR
    assert en_buyuk.tekrar_kimlik_yuzdesi > 80


def test_crispr_yok_ise_bos(tmp_path):
    yol = tmp_path / "rastgele.fasta"
    rng = random.Random(9)
    yol.write_text(">bos\n" + "".join(rng.choice("ACGT") for _ in range(5000)) + "\n")
    (kid, seq), = G.dizi_oku(yol)
    assert G.crispr_bul_crt(kid, seq) == []


def test_dizi_oku_desteklenmeyen(tmp_path):
    p = tmp_path / "x.txt"
    p.write_text("merhaba")
    with pytest.raises(ValueError):
        G.dizi_oku(p)


def test_genom_analiz_uctan_uca(tmp_path):
    yol = _crispr_fasta(tmp_path, aralayici=16)
    d = G.genom_analiz(yol, dosya_adi="crispr.fasta")
    assert d["kontig_sayisi"] == 1
    assert d["toplam_aralayici"] >= 12
    assert d["yontem_crispr"] in {"yerlesik-crt", "cctyper"}
    assert d["crispr_cas_tipi"]
    assert d["aciklama"]
    # üretilen dosyalar
    for anahtar in ("html_rapor", "pdf_rapor", "csv_rapor", "json_rapor"):
        assert d.get(anahtar), f"{anahtar} üretilmedi"


def test_ornek_genom_varsa_calisir():
    ornek = Path(__file__).resolve().parent.parent / "ornek_veri" / "genom" / "ornek_bakteri.fasta"
    if not ornek.exists():
        pytest.skip("örnek genom yok (scripts/ornek_genom_uret.py çalıştırın)")
    d = G.genom_analiz(ornek)
    assert d["toplam_aralayici"] >= 5
