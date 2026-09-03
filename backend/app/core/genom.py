"""Bakteriyel CRISPR-Cas ve genom benzerliği analizi.

Girdi: FASTA / GenBank / GFF bakteriyel DNA dosyası.

Boru hattı:
  1. Diziyi oku (Biopython).
  2. CRISPR dizilerini bul — yerleşik CRT tarzı tekrar/aralayıcı bulucu.
     `cctyper` (CRISPRCasTyper) kuruluysa Cas genleri + alt tip tiplemesi için de çağrılır.
  3. Cas gen adaylarını çıkar — `prodigal` ile ORF çağrısı + CRISPR lokuslarına
     yakınlık; `cctyper` varsa gerçek Cas operon çıktısı kullanılır.
  4. En yakın tür/suş — `skani` kuruluysa ve referans genom kümesi varsa ANI ile.
  5. Genom + CRISPR lokus haritası — `pyGenomeViz` ile.
  6. Sonuç: PNG, PDF, HTML, CSV, JSON.

`cctyper` / `skani` yoksa sistem yerleşik analizle çalışmaya devam eder; hangi
yöntemin kullanıldığı sonuçta raporlanır (Omnipose ↔ watershed ile aynı mantık).
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.config import ayarlari_al
from app.utils.dosya import benzersiz_ad
from app.utils.loglama import log_al

log = log_al(__name__)

# --- CRT tarzı bulucu parametreleri (MinCED/CRT varsayılanlarına yakın) ---
MIN_TEKRAR = 20
MAKS_TEKRAR = 48
MIN_ARALAYICI = 20
MAKS_ARALAYICI = 100
MIN_TEKRAR_SAYISI = 3
TOHUM = 11  # kesin eşleşen tohum uzunluğu


# --------------------------------------------------------------------------- #
# Veri sınıfları
# --------------------------------------------------------------------------- #
@dataclass
class CrisprDizisi:
    kontig: str
    baslangic: int
    bitis: int
    tekrar_uzunlugu: int
    tekrar_konsensus: str
    tekrar_sayisi: int
    aralayici_sayisi: int
    aralayicilar: list[str]
    ortalama_aralayici_uzunlugu: float
    tekrar_kimlik_yuzdesi: float

    def sozluk(self) -> dict:
        d = asdict(self)
        d["aralayicilar"] = self.aralayicilar[:200]
        return d


@dataclass
class CasGeni:
    kontig: str
    baslangic: int
    bitis: int
    yon: str
    ad: str            # cctyper varsa gen adı; yoksa "aday_cas"
    kaynak: str        # "cctyper" | "yakinlik"


@dataclass
class TurEslesme:
    tur: str
    ani_yuzdesi: float
    hizalanan_kesir: float
    referans: str


@dataclass
class GenomSonucu:
    dosya_adi: str
    kontig_sayisi: int
    toplam_uzunluk: int
    gc_yuzdesi: float
    yontem_crispr: str          # "cctyper" | "yerlesik-crt"
    yontem_tur: str             # "skani" | "referans-yok"
    crispr_cas_tipi: str        # cctyper alt tipi ya da "belirlenemedi (cctyper yok)"
    diziler: list[CrisprDizisi]
    cas_genleri: list[CasGeni]
    tur_eslesmesi: TurEslesme | None
    toplam_aralayici: int
    genom_haritasi: str | None      # göreli yol
    lokus_haritasi: str | None
    html_rapor: str | None
    aciklama: str
    uyarilar: list[str] = field(default_factory=list)

    def sozluk(self) -> dict:
        return {
            "dosya_adi": self.dosya_adi,
            "kontig_sayisi": self.kontig_sayisi,
            "toplam_uzunluk": self.toplam_uzunluk,
            "gc_yuzdesi": round(self.gc_yuzdesi, 2),
            "yontem_crispr": self.yontem_crispr,
            "yontem_tur": self.yontem_tur,
            "crispr_cas_tipi": self.crispr_cas_tipi,
            "toplam_aralayici": self.toplam_aralayici,
            "diziler": [d.sozluk() for d in self.diziler],
            "cas_genleri": [asdict(c) for c in self.cas_genleri],
            "tur_eslesmesi": asdict(self.tur_eslesmesi) if self.tur_eslesmesi else None,
            "genom_haritasi": self.genom_haritasi,
            "lokus_haritasi": self.lokus_haritasi,
            "html_rapor": self.html_rapor,
            "aciklama": self.aciklama,
            "uyarilar": self.uyarilar,
        }


# --------------------------------------------------------------------------- #
# Dizi okuma
# --------------------------------------------------------------------------- #
DESTEKLENEN = {".fasta", ".fa", ".fna", ".ffn", ".gb", ".gbk", ".genbank", ".gff", ".gff3"}


def _bicim(yol: Path) -> str:
    u = yol.suffix.lower()
    if u in {".gb", ".gbk", ".genbank"}:
        return "genbank"
    if u in {".gff", ".gff3"}:
        return "gff"
    return "fasta"


def dizi_oku(yol: str | Path) -> list[tuple[str, str]]:
    """(kontig_id, dizi) listesi döndürür. GFF'te FASTA bölümü aranır."""
    from Bio import SeqIO

    yol = Path(yol)
    if yol.suffix.lower() not in DESTEKLENEN:
        raise ValueError(
            "Desteklenmeyen dosya türü. FASTA (.fasta/.fa/.fna), GenBank (.gb/.gbk) "
            "veya GFF (.gff/.gff3) yükleyin."
        )
    bic = _bicim(yol)
    kayitlar: list[tuple[str, str]] = []

    if bic == "gff":
        metin = yol.read_text(errors="ignore")
        if "##FASTA" in metin:
            fasta_kismi = metin.split("##FASTA", 1)[1]
            gecici = Path(tempfile.mkstemp(suffix=".fasta")[1])
            gecici.write_text(fasta_kismi)
            for k in SeqIO.parse(str(gecici), "fasta"):
                kayitlar.append((k.id, str(k.seq).upper()))
            gecici.unlink(missing_ok=True)
        if not kayitlar:
            raise ValueError("GFF dosyasında gömülü FASTA (##FASTA) bölümü bulunamadı.")
    else:
        for k in SeqIO.parse(str(yol), bic):
            s = str(k.seq).upper()
            if s:
                kayitlar.append((k.id, s))

    if not kayitlar:
        raise ValueError("Dosyadan dizi okunamadı.")
    return kayitlar


def _gc(diziler: list[tuple[str, str]]) -> float:
    tum = "".join(s for _, s in diziler)
    if not tum:
        return 0.0
    return 100.0 * (tum.count("G") + tum.count("C")) / len(tum)


# --------------------------------------------------------------------------- #
# Yerleşik CRT tarzı CRISPR bulucu
# --------------------------------------------------------------------------- #
def _hamming(a: str, b: str) -> int:
    return sum(1 for x, y in zip(a, b) if x != y)


def _konsensus(tekrarlar: list[str]) -> str:
    if not tekrarlar:
        return ""
    n = min(len(t) for t in tekrarlar)
    kons = []
    for i in range(n):
        kons.append(Counter(t[i] for t in tekrarlar).most_common(1)[0][0])
    return "".join(kons)


def crispr_bul_crt(kontig_id: str, seq: str) -> list[CrisprDizisi]:
    """Kesin tohum eşleşmesi + esnek uzatma ile CRISPR dizilerini bulur."""
    n = len(seq)
    if n < 200:
        return []

    # tohum -> konumlar
    tohum_konum: dict[str, list[int]] = {}
    for i in range(n - TOHUM):
        tohum_konum.setdefault(seq[i:i + TOHUM], []).append(i)

    diziler: list[CrisprDizisi] = []
    kullanilan = [False] * n

    for i in range(n - TOHUM):
        if kullanilan[i]:
            continue
        tohum = seq[i:i + TOHUM]
        adaylar = [j for j in tohum_konum.get(tohum, [])
                   if MIN_TEKRAR + MIN_ARALAYICI <= j - i <= MAKS_TEKRAR + MAKS_ARALAYICI]
        if not adaylar:
            continue
        adim = adaylar[0] - i  # ilk periyot tahmini

        # Diziyi kur: i'den başlayarak ~adim aralıklarla tekrar kopyaları
        tekrar_bas = [i]
        son = i
        while True:
            hedef = son + adim
            en_iyi, en_iyi_fark = None, TOHUM
            for d in range(-6, 7):
                p = hedef + d
                if 0 <= p < n - TOHUM:
                    f = _hamming(seq[p:p + TOHUM], tohum)
                    if f < en_iyi_fark:
                        en_iyi, en_iyi_fark = p, f
            if en_iyi is None or en_iyi_fark > 3:
                break
            tekrar_bas.append(en_iyi)
            son = en_iyi
            adim = int(round((tekrar_bas[-1] - tekrar_bas[0]) / (len(tekrar_bas) - 1)))
            if len(tekrar_bas) > 400:
                break

        if len(tekrar_bas) < MIN_TEKRAR_SAYISI:
            continue

        # Tekrar uzunluğunu tahmin et: ardışık tohumlar arası boşluktan aralayıcı
        araliklar = [tekrar_bas[k + 1] - tekrar_bas[k] for k in range(len(tekrar_bas) - 1)]
        ort_aralik = sum(araliklar) / len(araliklar)
        # tekrar uzunluğu: tohumdan sağa doğru komşu kopyalarla eşleşen bölge
        tekrar_uz = TOHUM
        for uz in range(TOHUM + 1, MAKS_TEKRAR + 1):
            if tekrar_bas[0] + uz >= n:
                break
            ref = seq[tekrar_bas[0]:tekrar_bas[0] + uz]
            ok = 0
            for b in tekrar_bas[1:5]:
                if b + uz <= n and _hamming(seq[b:b + uz], ref) <= max(2, uz // 8):
                    ok += 1
            if ok >= min(2, len(tekrar_bas) - 1):
                tekrar_uz = uz
        if not (MIN_TEKRAR <= tekrar_uz <= MAKS_TEKRAR):
            continue

        tekrarlar = [seq[b:b + tekrar_uz] for b in tekrar_bas if b + tekrar_uz <= n]
        if len(tekrarlar) < MIN_TEKRAR_SAYISI:
            continue
        aralayicilar = []
        for k in range(len(tekrar_bas) - 1):
            s0 = tekrar_bas[k] + tekrar_uz
            s1 = tekrar_bas[k + 1]
            if MIN_ARALAYICI <= s1 - s0 <= MAKS_ARALAYICI + 40:
                aralayicilar.append(seq[s0:s1])
        if len(aralayicilar) < MIN_TEKRAR_SAYISI - 1:
            continue

        kons = _konsensus(tekrarlar)
        kimlik = 100.0 * sum(
            1 - _hamming(t[:len(kons)], kons) / max(len(kons), 1) for t in tekrarlar
        ) / len(tekrarlar)
        bas, bit = tekrar_bas[0], tekrar_bas[-1] + tekrar_uz
        for p in range(bas, min(bit, n)):
            kullanilan[p] = True

        diziler.append(CrisprDizisi(
            kontig=kontig_id, baslangic=bas + 1, bitis=bit,
            tekrar_uzunlugu=tekrar_uz, tekrar_konsensus=kons,
            tekrar_sayisi=len(tekrarlar), aralayici_sayisi=len(aralayicilar),
            aralayicilar=aralayicilar,
            ortalama_aralayici_uzunlugu=round(
                sum(len(a) for a in aralayicilar) / len(aralayicilar), 1),
            tekrar_kimlik_yuzdesi=round(kimlik, 1),
        ))

    # Çakışanları temizle, konuma göre sırala
    diziler.sort(key=lambda d: (d.kontig, d.baslangic))
    temiz: list[CrisprDizisi] = []
    for d in diziler:
        if temiz and d.kontig == temiz[-1].kontig and d.baslangic <= temiz[-1].bitis:
            continue
        temiz.append(d)
    return temiz


# --------------------------------------------------------------------------- #
# Harici araçlar (opsiyonel): cctyper, prodigal, skani
# --------------------------------------------------------------------------- #
def _arac_var(ad: str) -> bool:
    return shutil.which(ad) is not None


def cctyper_calistir(fasta_yolu: Path) -> dict | None:
    """CRISPRCasTyper — kurulu ve veritabanı yapılandırılmışsa Cas genleri + alt tip
    tiplemesi. Yoksa None (yerleşik analize düşülür)."""
    if not _arac_var("cctyper"):
        return None
    import os

    komut = ["cctyper", str(fasta_yolu), "OUT", "--no_plot"]
    db = os.getenv("CCTYPER_DB", "").strip()
    if db:
        komut += ["--db", db]
    cikti = Path(tempfile.mkdtemp(prefix="cctyper_"))
    komut[2] = str(cikti / "out")
    try:
        r = subprocess.run(komut, capture_output=True, text=True, timeout=300)
        od = cikti / "out"
        sonuc: dict = {"tip": None, "cas_operonlari": [], "crispr": []}
        cas_tab = od / "cas_operons.tab"
        if cas_tab.exists():
            satirlar = cas_tab.read_text().splitlines()
            basliklar = satirlar[0].split("\t") if satirlar else []
            for s in satirlar[1:]:
                a = dict(zip(basliklar, s.split("\t")))
                sonuc["cas_operonlari"].append(a)
                if a.get("Prediction") and not sonuc["tip"]:
                    sonuc["tip"] = a["Prediction"]
        cr_tab = od / "crisprs_all.tab"
        if cr_tab.exists():
            satirlar = cr_tab.read_text().splitlines()
            basliklar = satirlar[0].split("\t") if satirlar else []
            for s in satirlar[1:]:
                sonuc["crispr"].append(dict(zip(basliklar, s.split("\t"))))
        # cctyper'ın asıl katkısı Cas gen tiplemesidir (HMM veritabanı gerektirir).
        # Sadece CRISPR dizisi bulup Cas typing yapamadıysa, yerleşik analizle
        # tutarlılık için None döneriz.
        if not sonuc["cas_operonlari"]:
            if r.returncode != 0:
                log.info("cctyper Cas tiplemesi yapamadı (%s). Yerleşik analiz kullanılacak.",
                         (r.stderr or "").strip().splitlines()[-1] if r.stderr else "veritabanı yok")
            return None
        return sonuc
    except Exception as e:  # pragma: no cover
        log.warning("cctyper çalıştırılamadı (%s). Yerleşik analize düşülüyor.", e)
        return None
    finally:
        shutil.rmtree(cikti, ignore_errors=True)


def prodigal_orf(fasta_yolu: Path) -> list[tuple[str, int, int, str]]:
    """(kontig, bas, bit, yon) ORF listesi. prodigal yoksa boş."""
    if not _arac_var("prodigal"):
        return []
    gff = Path(tempfile.mkstemp(suffix=".gff")[1])
    try:
        subprocess.run(
            ["prodigal", "-i", str(fasta_yolu), "-f", "gff", "-o", str(gff),
             "-p", "meta", "-q"],
            capture_output=True, timeout=300, check=False,
        )
        orfler = []
        for satir in gff.read_text().splitlines():
            if satir.startswith("#") or "\tCDS\t" not in satir:
                continue
            p = satir.split("\t")
            orfler.append((p[0], int(p[3]), int(p[4]), p[6]))
        return orfler
    except Exception as e:  # pragma: no cover
        log.warning("prodigal çalıştırılamadı (%s).", e)
        return []
    finally:
        gff.unlink(missing_ok=True)


def skani_tur_bul(fasta_yolu: Path) -> TurEslesme | None:
    """skani + paketlenmiş referans genom kümesiyle en yakın tür/suş."""
    if not _arac_var("skani"):
        return None
    ref_dizin = Path(__file__).resolve().parent.parent.parent / "ornek_veri" / "genom" / "referans"
    refler = sorted(p for p in ref_dizin.glob("*") if p.suffix.lower() in {".fasta", ".fa", ".fna"})
    if not refler:
        return None
    try:
        r = subprocess.run(
            ["skani", "dist", "-q", str(fasta_yolu), "-r", *map(str, refler),
             "--min-af", "5", "-o", "/dev/stdout"],
            capture_output=True, text=True, timeout=180,
        )
        satirlar = [s for s in r.stdout.splitlines() if s and not s.startswith("Ref_file")]
        if not satirlar:
            return None
        en_iyi = max(satirlar, key=lambda s: float(s.split("\t")[2] or 0))
        p = en_iyi.split("\t")
        ref_ad = Path(p[0]).stem
        return TurEslesme(
            tur=ref_ad.replace("_", " "),
            ani_yuzdesi=round(float(p[2]), 2),
            hizalanan_kesir=round(float(p[3]), 2),
            referans=ref_ad,
        )
    except Exception as e:  # pragma: no cover
        log.warning("skani çalıştırılamadı (%s).", e)
        return None


# --------------------------------------------------------------------------- #
# Görselleştirme — pyGenomeViz (karşılaştırmalı çoklu-genom sinteni)
# --------------------------------------------------------------------------- #
@dataclass
class GenomKaydi:
    """Bir genom dosyasının çözümlenmiş hâli."""

    ad: str
    yol: Path
    kontigler: list[tuple[str, str]]        # (seqid, dizi)
    genler: list[tuple[str, int, int, int, str]]  # (seqid, bas, bit, yön, etiket)
    crispr: list[CrisprDizisi]
    cas: list[CasGeni]
    tur: "TurEslesme | None"
    kaynak_genbank: bool

    @property
    def toplam_uzunluk(self) -> int:
        return sum(len(s) for _, s in self.kontigler)

    @property
    def gc(self) -> float:
        return _gc(self.kontigler)


def genler_al(yol: Path, kontigler: list[tuple[str, str]]) -> tuple[list, bool]:
    """GenBank ise açıklamalı CDS'leri; değilse prodigal ORF'lerini döndürür.

    Dönüş: ([(seqid, bas, bit, yön(±1), etiket)], genbank_mi)
    """
    genler: list[tuple[str, int, int, int, str]] = []
    if _bicim(yol) == "genbank":
        try:
            from Bio import SeqIO

            for rec in SeqIO.parse(str(yol), "genbank"):
                for f in rec.features:
                    if f.type not in ("CDS", "gene"):
                        continue
                    q = f.qualifiers
                    etiket = (q.get("gene", q.get("product", [""]))[0] or "")[:24]
                    genler.append((
                        rec.id, int(f.location.start) + 1, int(f.location.end),
                        1 if f.location.strand in (None, 1) else -1, etiket,
                    ))
            if genler:
                # aynı gen/CDS çiftinden yalnızca birini tut
                benzersiz = {}
                for g in genler:
                    benzersiz[(g[0], g[1], g[2])] = g
                return list(benzersiz.values()), True
        except Exception as e:  # pragma: no cover
            log.warning("GenBank özellikleri okunamadı (%s), prodigal denenecek.", e)

    # FASTA / açıklaması olmayan GenBank → prodigal
    fasta = yol
    if _bicim(yol) != "fasta":
        fasta = Path(tempfile.mkstemp(suffix=".fasta")[1])
        fasta.write_text("".join(f">{k}\n{s}\n" for k, s in kontigler))
    for kontig, b, e, yon in prodigal_orf(fasta):
        genler.append((kontig, b, e, 1 if yon == "+" else -1, ""))
    if fasta != yol:
        fasta.unlink(missing_ok=True)
    return genler, False


def _hizalamalar(yollar: list[Path]) -> tuple[list, str]:
    """Komşu genom çiftleri arası sinteni.

    GenBank girdilerde pyGenomeViz `MMseqs` (protein RBH — repo faj örneğiyle aynı);
    FASTA girdilerde `MUMmer` (nükleotid). Dönüş: (AlignCoord listesi, yöntem adı).
    """
    if len(yollar) < 2:
        return [], "yok"
    hepsi_gbk = all(_bicim(p) == "genbank" for p in yollar)
    denemeler = []
    if hepsi_gbk:
        denemeler = [("mmseqs", "MMseqs"), ("mummer", "MUMmer")]
    else:
        denemeler = [("mummer", "MUMmer"), ("mmseqs", "MMseqs")]
    for anahtar, sinif_ad in denemeler:
        try:
            from pygenomeviz import align

            Sinif = getattr(align, sinif_ad)
            coords = Sinif(list(yollar)).run()
            if coords:
                return coords, anahtar
        except Exception as e:
            log.info("%s sinteni hesaplanamadı (%s).", sinif_ad, e)
    log.warning("Sinteni hizalaması yapılamadı. Bağlantısız harita çizilecek.")
    return [], "yok"


def karsilastirmali_harita(
    genomlar: list[GenomKaydi], hizalamalar: list, cikti_dizini: Path
) -> tuple[Path | None, Path | None]:
    """pyGenomeViz ile çoklu-genom karşılaştırma figürü.

    Repo örneklerindeki gibi: her genom bir parça (track), turuncu gen okları,
    genomlar arası kimliğe göre renklendirilmiş sinteni bağlantıları, CRISPR
    dizileri ve Cas genleri işaretli. (PNG + HTML)
    """
    import matplotlib

    matplotlib.use("Agg")
    from pygenomeviz import GenomeViz

    tekli = len(genomlar) == 1
    gv = GenomeViz(
        fig_track_height=0.6 if not tekli else 0.9,
        feature_track_ratio=0.5,
        show_axis=True,
    )
    for g in genomlar:
        boy = {sid: len(s) for sid, s in g.kontigler}
        trk = gv.add_feature_track(g.ad[:26], boy)
        # gen okları
        for sid, b, e, yon, etiket in g.genler:
            uzun = boy.get(sid, e)
            try:
                trk.add_feature(max(int(b), 1), min(int(e), uzun), yon,
                                plotstyle="bigarrow", fc="#f0a020", ec="#c67c11",
                                lw=0.2, label=etiket if tekli and etiket else "")
            except Exception:
                continue
        # CRISPR dizileri
        for c in g.crispr:
            uzun = boy.get(c.kontig) or c.bitis
            trk.add_feature(max(int(c.baslangic), 1), min(int(c.bitis), uzun), 1,
                            plotstyle="bigbox", fc="#0891b2", ec="#0e7490", lw=0.7,
                            label=f"CRISPR·{c.aralayici_sayisi}" if tekli else "")
        # Cas gen adayları
        for cg in g.cas:
            uzun = boy.get(cg.kontig) or cg.bitis
            trk.add_feature(max(int(cg.baslangic), 1), min(int(cg.bitis), uzun),
                            1 if cg.yon == "+" else -1, plotstyle="bigarrow",
                            fc="#dc2626", ec="#991b1b", lw=0.3,
                            label=cg.ad if tekli and cg.ad != "aday_cas" else "")

    # Sinteni bağlantıları (kimliğe göre gri→kırmızı; ters yönlüler kırmızı)
    baglanti = 0
    for c in hizalamalar:
        try:
            q = getattr(c, "query_link", None)
            r = getattr(c, "ref_link", None)
            if not q or not r:
                continue
            gv.add_link(q, r, v=float(getattr(c, "identity", 100.0)),
                        vmin=30, vmax=100, curve=True,
                        color="#bdbdbd", inverted_color="#e33d3d")
            baglanti += 1
        except Exception:
            continue
    if baglanti:
        try:
            gv.set_colorbar(["#f2f2f2", "#b3121a"], vmin=30, vmax=100,
                            bar_label="Kimlik %", bar_labelsize=10, tick_labelsize=8,
                            bar_left=1.03)
        except Exception:
            pass
    try:
        gv.set_scale_bar()
    except Exception:
        pass

    fig = gv.plotfig()
    png = cikti_dizini / f"genom_karsilastirma_{benzersiz_ad('.png')}"
    fig.savefig(png, dpi=150, bbox_inches="tight")
    import matplotlib.pyplot as plt

    plt.close(fig)

    html = None
    try:
        html = cikti_dizini / f"genom_karsilastirma_{benzersiz_ad('.html')}"
        gv.savefig_html(str(html))
    except Exception as e:  # pragma: no cover
        log.info("pyGenomeViz HTML üretilemedi: %s", e)
        html = None
    return png, html


def _lokus_ciz(dizi: CrisprDizisi, cikti_dizini: Path) -> Path:
    """En büyük CRISPR dizisi için tekrar/aralayıcı şeması."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.patches as mpatches
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(min(14, 2 + dizi.aralayici_sayisi * 0.5), 1.6))
    x = 0
    tuz = max(dizi.tekrar_uzunlugu, 8)
    for i in range(dizi.tekrar_sayisi):
        ax.add_patch(mpatches.Rectangle((x, 0), tuz, 1, facecolor="#0891b2"))
        x += tuz
        if i < len(dizi.aralayicilar):
            sp = max(len(dizi.aralayicilar[i]), 8)
            ax.add_patch(mpatches.Rectangle((x, 0.15), sp, 0.7, facecolor="#e2e8f0",
                                            edgecolor="#94a3b8"))
            ax.text(x + sp / 2, 0.5, str(i + 1), ha="center", va="center", fontsize=7)
            x += sp
    ax.set_xlim(0, x)
    ax.set_ylim(-0.3, 1.3)
    ax.axis("off")
    ax.set_title(
        f"CRISPR lokusu — {dizi.tekrar_sayisi} tekrar (mavi), "
        f"{dizi.aralayici_sayisi} aralayıcı · tekrar konsensüsü: {dizi.tekrar_konsensus}",
        fontsize=9,
    )
    yol = cikti_dizini / f"crispr_lokus_{benzersiz_ad('.png')}"
    fig.savefig(yol, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return yol


def _html_rapor(sonuc: "GenomSonucu", cikti_dizini: Path) -> Path:
    yol = cikti_dizini / f"genom_rapor_{benzersiz_ad('.html')}"
    satir = []
    for d in sonuc.diziler:
        satir.append(
            f"<tr><td>{d.kontig}</td><td>{d.baslangic}-{d.bitis}</td>"
            f"<td>{d.tekrar_sayisi}</td><td>{d.aralayici_sayisi}</td>"
            f"<td><code>{d.tekrar_konsensus}</code></td>"
            f"<td>%{d.tekrar_kimlik_yuzdesi}</td></tr>"
        )
    tur = (
        f"{sonuc.tur_eslesmesi.tur} (ANI %{sonuc.tur_eslesmesi.ani_yuzdesi})"
        if sonuc.tur_eslesmesi else "Referans kümesi yapılandırılmadı"
    )
    yol.write_text(f"""<!doctype html><html lang="tr"><meta charset="utf-8">
<title>BioMine Vision — Genom / CRISPR-Cas Raporu</title>
<style>body{{font-family:system-ui;margin:2rem;color:#0f172a}}
h1{{color:#0e7490}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #cbd5e1;padding:6px 10px;text-align:left;font-size:14px}}
th{{background:#0f172a;color:#fff}}code{{font-size:12px}}</style>
<h1>Genom / CRISPR-Cas Raporu</h1>
<p><b>Dosya:</b> {sonuc.dosya_adi} &nbsp; <b>Kontig:</b> {sonuc.kontig_sayisi}
&nbsp; <b>Uzunluk:</b> {sonuc.toplam_uzunluk:,} bp &nbsp; <b>GC:</b> %{sonuc.gc_yuzdesi:.1f}</p>
<p><b>En yakın tür/suş:</b> {tur}<br>
<b>CRISPR-Cas tipi:</b> {sonuc.crispr_cas_tipi}<br>
<b>Toplam aralayıcı:</b> {sonuc.toplam_aralayici} &nbsp;
<b>Cas gen adayı:</b> {len(sonuc.cas_genleri)} &nbsp;
<b>CRISPR yöntemi:</b> {sonuc.yontem_crispr}</p>
<h2>CRISPR dizileri</h2>
<table><tr><th>Kontig</th><th>Konum</th><th>Tekrar</th><th>Aralayıcı</th>
<th>Tekrar konsensüsü</th><th>Kimlik</th></tr>{''.join(satir) or '<tr><td colspan=6>Dizi bulunamadı</td></tr>'}</table>
<h2>Açıklama</h2><p>{sonuc.aciklama}</p>
<p style="color:#64748b;font-size:12px">Bu sonuç yapay zekâ destekli ön analizdir;
laboratuvar doğrulamasının yerine geçmez.</p></html>""", encoding="utf-8")
    return yol


def _pdf_rapor(sonuc: "GenomSonucu", harita_png: Path | None,
               lokus_png: Path | None, cikti_dizini: Path) -> Path:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (Image, Paragraph, SimpleDocTemplate, Spacer,
                                    Table, TableStyle)

    yol = cikti_dizini / f"genom_rapor_{benzersiz_ad('.pdf')}"
    st = getSampleStyleSheet()
    o = [Paragraph("BioMine Vision — Genom / CRISPR-Cas Raporu", st["Title"]),
         Paragraph("ReLoop AI — Bakteriyel DNA Analizi", st["Normal"]),
         Spacer(1, 0.4 * cm)]
    ozet = [
        ["Alan", "Değer"],
        ["Dosya", sonuc.dosya_adi],
        ["Kontig sayısı", sonuc.kontig_sayisi],
        ["Toplam uzunluk (bp)", f"{sonuc.toplam_uzunluk:,}"],
        ["GC (%)", f"{sonuc.gc_yuzdesi:.1f}"],
        ["En yakın tür/suş",
         f"{sonuc.tur_eslesmesi.tur} (ANI %{sonuc.tur_eslesmesi.ani_yuzdesi})"
         if sonuc.tur_eslesmesi else "Referans kümesi yok"],
        ["CRISPR-Cas tipi", sonuc.crispr_cas_tipi],
        ["CRISPR dizisi sayısı", len(sonuc.diziler)],
        ["Toplam aralayıcı", sonuc.toplam_aralayici],
        ["Cas gen adayı", len(sonuc.cas_genleri)],
        ["Yöntem (CRISPR / tür)", f"{sonuc.yontem_crispr} / {sonuc.yontem_tur}"],
    ]
    t = Table(ozet, colWidths=[6 * cm, 9 * cm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0f172a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("FONTSIZE", (0, 0), (-1, -1), 9)]))
    o += [t, Spacer(1, 0.4 * cm)]
    if lokus_png and Path(lokus_png).exists():
        o += [Paragraph("CRISPR lokus haritası", st["Heading3"]),
              Image(str(lokus_png), width=16 * cm, height=4 * cm, kind="proportional")]
    if harita_png and Path(harita_png).exists():
        o += [Spacer(1, 0.3 * cm), Paragraph("Genom haritası", st["Heading3"]),
              Image(str(harita_png), width=16 * cm, height=8 * cm, kind="proportional")]
    o += [Spacer(1, 0.4 * cm), Paragraph("Açıklama", st["Heading3"]),
          Paragraph(sonuc.aciklama, st["Normal"]),
          Spacer(1, 0.3 * cm),
          Paragraph("Bu sonuç yapay zekâ destekli ön analizdir; laboratuvar "
                    "doğrulamasının yerine geçmez.", st["Italic"])]
    SimpleDocTemplate(str(yol), pagesize=A4).build(o)
    return yol


# --------------------------------------------------------------------------- #
# Orkestrasyon
# --------------------------------------------------------------------------- #
def _aciklama_uret(sonuc: "GenomSonucu") -> str:
    p = []
    if sonuc.tur_eslesmesi:
        p.append(
            f"Genom, referans kümesindeki en çok \"{sonuc.tur_eslesmesi.tur}\" ile "
            f"benziyor (ANI %{sonuc.tur_eslesmesi.ani_yuzdesi}, hizalanan kesir "
            f"%{sonuc.tur_eslesmesi.hizalanan_kesir}). ANI %95 üzeri genelde aynı tür kabul edilir."
        )
    else:
        p.append(
            "Tür ataması yapılmadı: skani kurulu değil veya referans genom kümesi "
            "yapılandırılmadı. Üretimde GTDB temsili genomlarıyla çalıştırın."
        )
    if sonuc.diziler:
        buyuk = max(sonuc.diziler, key=lambda d: d.aralayici_sayisi)
        p.append(
            f"{len(sonuc.diziler)} CRISPR dizisi bulundu; toplam {sonuc.toplam_aralayici} "
            f"aralayıcı. En büyük dizide {buyuk.tekrar_sayisi} tekrar ve "
            f"{buyuk.aralayici_sayisi} aralayıcı var; tekrar konsensüsü "
            f"{buyuk.tekrar_konsensus} (kimlik %{buyuk.tekrar_kimlik_yuzdesi}). "
            f"Aralayıcı sayısı, bakterinin geçmişte karşılaştığı faj/plazmid çeşitliliği "
            f"hakkında fikir verir."
        )
    else:
        p.append("Belirgin bir CRISPR dizisi bulunamadı.")
    if sonuc.crispr_cas_tipi.startswith("belirlenemedi"):
        p.append(
            f"Cas gen tiplemesi için CRISPRCasTyper (cctyper) gerekir. "
            f"Yakınlık temelli {len(sonuc.cas_genleri)} Cas gen adayı işaretlendi."
        )
    else:
        p.append(
            f"CRISPRCasTyper tiplemesi: {sonuc.crispr_cas_tipi}. "
            f"{len(sonuc.cas_genleri)} Cas geni bildirildi."
        )
    if sonuc.uyarilar:
        p.append("Uyarılar: " + " ".join(f"• {u}" for u in sonuc.uyarilar))
    return " ".join(p)


def _tek_genom_coz(
    yol: Path, *, uyarilar: list[str], tur_ata: bool = True
) -> tuple["GenomKaydi", str, str]:
    """Bir genom dosyasını çözer: kontig, gen, CRISPR, Cas, tür.

    Dönüş: (GenomKaydi, crispr_cas_tipi, crispr_yöntemi)
    """
    diziler_dna = dizi_oku(yol)
    toplam_uz = sum(len(s) for _, s in diziler_dna)
    if toplam_uz > 15_000_000:
        uyarilar.append("Genom büyük; yerleşik CRISPR taraması uzun sürebilir.")

    fasta_yolu = yol
    if _bicim(yol) != "fasta":
        fasta_yolu = Path(tempfile.mkstemp(suffix=".fasta")[1])
        fasta_yolu.write_text("".join(f">{kid}\n{s}\n" for kid, s in diziler_dna))

    cc = cctyper_calistir(fasta_yolu)
    crispr: list[CrisprDizisi] = []
    cas: list[CasGeni] = []
    tip = "belirlenemedi (cctyper yok)"
    yontem_crispr = "yerlesik-crt"

    if cc:
        yontem_crispr = "cctyper"
        for c in cc.get("crispr", []):
            try:
                sp = int(c.get("N_spacers") or c.get("Spacers") or 0)
                crispr.append(CrisprDizisi(
                    kontig=c.get("Contig", "?"),
                    baslangic=int(float(c.get("Start", 0))),
                    bitis=int(float(c.get("End", 0))),
                    tekrar_uzunlugu=len(c.get("Consensus_repeat", "") or ""),
                    tekrar_konsensus=c.get("Consensus_repeat", "") or "",
                    tekrar_sayisi=sp + 1, aralayici_sayisi=sp, aralayicilar=[],
                    ortalama_aralayici_uzunlugu=float(c.get("Spacer_len_avg", 0) or 0),
                    tekrar_kimlik_yuzdesi=float(c.get("Repeat_identity", 0) or 0),
                ))
            except Exception:
                continue
        for op in cc.get("cas_operonlari", []):
            genler = (op.get("Genes") or "").strip("[]").replace("'", "")
            for g in [x.strip() for x in genler.split(",") if x.strip()]:
                cas.append(CasGeni(kontig=op.get("Contig", "?"),
                                   baslangic=int(float(op.get("Start", 0))),
                                   bitis=int(float(op.get("End", 0))),
                                   yon="+", ad=g, kaynak="cctyper"))
            if op.get("Prediction"):
                tip = op["Prediction"]
        if tip == "belirlenemedi (cctyper yok)":
            tip = "cctyper: alt tip atanamadı"

    if not crispr:
        from Bio.Seq import Seq

        for kid, s in diziler_dna:
            n = len(s)
            ileri = crispr_bul_crt(kid, s)
            geri = crispr_bul_crt(kid, str(Seq(s).reverse_complement()))
            # RC koordinatlarını ileri şeride çevir
            for d in geri:
                yeni_bas = n - d.bitis + 1
                yeni_bit = n - d.baslangic + 1
                d.baslangic, d.bitis = max(1, yeni_bas), yeni_bit
            hepsi = sorted(ileri + geri, key=lambda d: d.baslangic)
            # Genomik olarak çakışanlarda en çok aralayıcılıyı tut
            for d in hepsi:
                cakisan = next(
                    (x for x in crispr if x.kontig == kid
                     and not (d.bitis < x.baslangic or d.baslangic > x.bitis)),
                    None,
                )
                if cakisan is None:
                    crispr.append(d)
                elif d.aralayici_sayisi > cakisan.aralayici_sayisi:
                    crispr[crispr.index(cakisan)] = d

    # Cas adayları — cctyper yoksa prodigal ORF + CRISPR yakınlığı
    if not cas and crispr:
        orfler = prodigal_orf(fasta_yolu)
        for kontig, b, e, yon in orfler:
            for d in crispr:
                if d.kontig == kontig and abs(b - d.baslangic) < 20000:
                    cas.append(CasGeni(kontig, b, e, yon, "aday_cas", "yakinlik"))
                    break
        if len(cas) > 60:
            cas = cas[:60]
            uyarilar.append("Çok sayıda Cas gen adayı; ilk 60 gösteriliyor.")

    tur = skani_tur_bul(fasta_yolu) if tur_ata else None

    genler, gbk_mi = genler_al(yol, diziler_dna)

    kayit = GenomKaydi(
        ad=Path(yol).stem, yol=Path(yol), kontigler=diziler_dna, genler=genler,
        crispr=crispr, cas=cas, tur=tur, kaynak_genbank=gbk_mi,
    )
    if fasta_yolu != yol:
        fasta_yolu.unlink(missing_ok=True)
    return kayit, tip, yontem_crispr


def genom_analiz(yol, *, dosya_adi: str | None = None) -> dict:
    """Tek veya çoklu genom analizi.

    `yol` tek bir dosya yolu ya da dosya yolları listesi olabilir. Birden çok
    genom verilirse pyGenomeViz ile karşılaştırmalı sinteni figürü üretilir.
    """
    ayar = ayarlari_al()
    cikti = ayar.cikti_dizini
    cikti.mkdir(parents=True, exist_ok=True)
    uyarilar: list[str] = []

    yollar = [Path(p) for p in (yol if isinstance(yol, (list, tuple)) else [yol])]
    coklu = len(yollar) > 1

    genom_kayitlari: list[GenomKaydi] = []
    tipler: list[str] = []
    yontemler: list[str] = []
    for p in yollar:
        try:
            k, tp, ym = _tek_genom_coz(p, uyarilar=uyarilar)
            genom_kayitlari.append(k)
            tipler.append(tp)
            yontemler.append(ym)
        except ValueError:
            raise
        except Exception as e:
            log.exception("Genom çözümlenemedi: %s", p)
            uyarilar.append(f"{p.name} çözümlenemedi: {e}")

    if not genom_kayitlari:
        raise ValueError("Hiçbir genom dosyası okunamadı.")

    ilk = genom_kayitlari[0]
    tip = next((t for t in tipler if not t.startswith("belirlenemedi")), tipler[0])
    yontem_crispr = "cctyper" if "cctyper" in yontemler else "yerlesik-crt"
    yontem_tur = "skani" if any(k.tur for k in genom_kayitlari) else "referans-yok"
    dosya_adi = dosya_adi or (
        f"{len(genom_kayitlari)} genom karşılaştırması" if coklu else ilk.yol.name
    )

    toplam_aralayici = sum(d.aralayici_sayisi for k in genom_kayitlari for d in k.crispr)

    sonuc = GenomSonucu(
        dosya_adi=dosya_adi,
        kontig_sayisi=sum(len(k.kontigler) for k in genom_kayitlari),
        toplam_uzunluk=sum(k.toplam_uzunluk for k in genom_kayitlari),
        gc_yuzdesi=ilk.gc,
        yontem_crispr=yontem_crispr,
        yontem_tur=yontem_tur,
        crispr_cas_tipi=tip,
        diziler=[d for k in genom_kayitlari for d in k.crispr],
        cas_genleri=[c for k in genom_kayitlari for c in k.cas],
        tur_eslesmesi=ilk.tur,
        toplam_aralayici=toplam_aralayici,
        genom_haritasi=None, lokus_haritasi=None, html_rapor=None,
        aciklama="", uyarilar=uyarilar,
    )
    sonuc.aciklama = _aciklama_uret(sonuc)
    if coklu:
        adlar = ", ".join(k.ad for k in genom_kayitlari)
        sonuc.aciklama = (
            f"{len(genom_kayitlari)} genom karşılaştırıldı ({adlar}). "
            + sonuc.aciklama
        )

    crispr = sonuc.diziler

    # --- Karşılaştırmalı / tekli genom haritası (pyGenomeViz) ---
    hizalamalar, hiz_yontem = (
        _hizalamalar([k.yol for k in genom_kayitlari]) if coklu else ([], "yok")
    )
    harita_html = None
    try:
        png, harita_html = karsilastirmali_harita(genom_kayitlari, hizalamalar, cikti)
        if png:
            sonuc.genom_haritasi = _rel(png, ayar.veri_dizini)
    except Exception as e:
        log.warning("Genom haritası çizilemedi: %s", e)
        uyarilar.append("Genom haritası oluşturulamadı.")

    if crispr:
        try:
            buyuk = max(crispr, key=lambda d: d.aralayici_sayisi)
            lp = _lokus_ciz(buyuk, cikti)
            sonuc.lokus_haritasi = _rel(lp, ayar.veri_dizini)
        except Exception as e:  # pragma: no cover
            log.warning("Lokus haritası çizilemedi: %s", e)

    try:
        hp = _html_rapor(sonuc, cikti)
        sonuc.html_rapor = _rel(hp, ayar.veri_dizini)
    except Exception as e:  # pragma: no cover
        log.warning("HTML rapor yazılamadı: %s", e)

    d = sonuc.sozluk()

    # PDF
    try:
        pdf = _pdf_rapor(
            sonuc,
            ayar.veri_dizini / sonuc.genom_haritasi if sonuc.genom_haritasi else None,
            ayar.veri_dizini / sonuc.lokus_haritasi if sonuc.lokus_haritasi else None,
            cikti,
        )
        d["pdf_rapor"] = _rel(pdf, ayar.veri_dizini)
    except Exception as e:  # pragma: no cover
        log.warning("PDF rapor yazılamadı: %s", e)
        d["pdf_rapor"] = None

    # CSV (aralayıcı tablosu) + JSON (tam sonuç)
    csv_yol = cikti / f"genom_aralayicilar_{benzersiz_ad('.csv')}"
    with csv_yol.open("w", encoding="utf-8") as f:
        f.write("dizi,kontig,konum,aralayici_no,aralayici_uzunlugu,aralayici_dizisi\n")
        for di, dz in enumerate(sonuc.diziler, 1):
            for si, sp in enumerate(dz.aralayicilar, 1):
                f.write(f"{di},{dz.kontig},{dz.baslangic}-{dz.bitis},{si},{len(sp)},{sp}\n")
    d["csv_rapor"] = _rel(csv_yol, ayar.veri_dizini)

    # --- Çoklu genom alanları ---
    d["genom_sayisi"] = len(genom_kayitlari)
    d["karsilastirmali"] = coklu
    d["hizalama_sayisi"] = len(hizalamalar)
    d["hizalama_yontemi"] = hiz_yontem
    d["karsilastirma_html"] = _rel(harita_html, ayar.veri_dizini) if harita_html else None
    d["genomlar"] = [
        {
            "ad": k.ad,
            "kontig_sayisi": len(k.kontigler),
            "toplam_uzunluk": k.toplam_uzunluk,
            "gc_yuzdesi": round(k.gc, 2),
            "gen_sayisi": len(k.genler),
            "gen_kaynagi": "genbank" if k.kaynak_genbank else ("prodigal" if k.genler else "yok"),
            "crispr_dizisi": len(k.crispr),
            "toplam_aralayici": sum(x.aralayici_sayisi for x in k.crispr),
            "cas_gen_adayi": len(k.cas),
            "tur_eslesmesi": asdict(k.tur) if k.tur else None,
            "diziler": [x.sozluk() for x in k.crispr],
        }
        for k in genom_kayitlari
    ]

    json_yol = cikti / f"genom_sonuc_{benzersiz_ad('.json')}"
    json_yol.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    d["json_rapor"] = _rel(json_yol, ayar.veri_dizini)
    return d


def _rel(yol: Path, kok: Path) -> str:
    try:
        return str(Path(yol).resolve().relative_to(Path(kok).resolve()))
    except ValueError:
        return str(yol)
