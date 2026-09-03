"""Hücre takibi (cell tracking) — zaman serisi görüntülerde hücre soyağacı.

Girdi: MP4/AVI video, çok sayfalı TIFF ya da kare görüntülerini içeren ZIP.

Boru hattı:
  1. Kareleri çıkar.
  2. Her kareyi segmentle (mevcut `segmentasyon` modülü — Omnipose ya da watershed).
  3. Kareler arası hücreleri eşle:
     * `trackastra` kuruluysa transformer tabanlı model ile,
     * değilse yerleşik IoU + merkez uzaklığı + Macar algoritması (scipy) ile.
  4. Kalıcı iz kimlikleri, doğum/ölüm ve bölünme (division) olayları.
  5. İz kaplamalı kareler + MP4, sayım grafiği, CSV/JSON.

Mevcut analiz akışına dokunmaz; tamamen ek bir modüldür.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import cv2
import numpy as np

from app.config import ayarlari_al
from app.core import morfoloji, on_isleme, segmentasyon
from app.utils.dosya import benzersiz_ad
from app.utils.loglama import log_al

log = log_al(__name__)

PALET = morfoloji.PALET
MAKS_KARE = 60
ESLESME_ESIGI = 0.72      # birleşik maliyet bunun üstündeyse eşleşme yok
MAKS_MERKEZ_UZAKLIK = 90  # px — bundan uzak hücreler aynı iz sayılmaz


@dataclass
class IzNoktasi:
    kare: int
    zaman_sn: float
    x: float
    y: float
    alan: float


@dataclass
class Iz:
    id: int
    parent_id: int | None
    noktalar: list[IzNoktasi] = field(default_factory=list)

    @property
    def baslangic_kare(self) -> int:
        return self.noktalar[0].kare

    @property
    def bitis_kare(self) -> int:
        return self.noktalar[-1].kare

    @property
    def sure_kare(self) -> int:
        return self.bitis_kare - self.baslangic_kare + 1


# --------------------------------------------------------------------------- #
# Kare çıkarma
# --------------------------------------------------------------------------- #
def _kareler(yol: Path, aralik_sn: float) -> list[tuple[int, float, np.ndarray]]:
    u = yol.suffix.lower()
    if u in {".mp4", ".avi", ".mov", ".mkv"}:
        from app.core.video import kareleri_cikar

        return kareleri_cikar(yol, aralik_sn=aralik_sn, maks_kare=MAKS_KARE)
    if u in {".tif", ".tiff"}:
        import imageio.v3 as iio

        yigin = iio.imread(yol)
        if yigin.ndim == 2:
            yigin = yigin[None]
        kareler = []
        for i, kare in enumerate(yigin[:MAKS_KARE]):
            rgb = on_isleme._rgb_uint8(kare)
            kareler.append((i, round(i * aralik_sn, 2), rgb))
        return kareler
    if u == ".zip":
        import zipfile

        # Kaynak dosyanın yanına değil, ayrılmış çalışma dizinine aç.
        hedef = ayarlari_al().yukleme_dizini / "takip" / f"kare_{benzersiz_ad('')}"
        hedef.mkdir(parents=True, exist_ok=True)
        gorseller: list[Path] = []
        with zipfile.ZipFile(yol) as z:
            adlar = sorted(
                i.filename for i in z.infolist()
                if not i.is_dir()
                and Path(i.filename).suffix.lower() in on_isleme.DESTEKLENEN_UZANTILAR
            )
            for ad in adlar:
                cikan = hedef / Path(ad).name
                cikan.write_bytes(z.read(ad))
                gorseller.append(cikan)
        return [
            (i, round(i * aralik_sn, 2), on_isleme.goruntu_oku(g))
            for i, g in enumerate(gorseller[:MAKS_KARE])
        ]
    raise ValueError(
        "Desteklenmeyen dosya. MP4/AVI video, çok sayfalı TIFF veya kare "
        "görüntüleri içeren ZIP yükleyin."
    )


# --------------------------------------------------------------------------- #
# Segmentasyon → nesne listesi
# --------------------------------------------------------------------------- #
@dataclass
class _Nesne:
    etiket: int
    x: float
    y: float
    alan: float
    maske: np.ndarray  # bool


def _kare_nesneleri(rgb: np.ndarray, omnipose_model: str) -> tuple[list[_Nesne], np.ndarray]:
    on = on_isleme.on_isle(rgb, gurultu_azaltma=False)
    seg = segmentasyon.segmentle(on.gri, omnipose_model=omnipose_model)
    etiketler = seg.etiket_haritasi
    from skimage.measure import regionprops

    nesneler = []
    for b in regionprops(etiketler):
        if b.area < 8:
            continue
        nesneler.append(_Nesne(
            etiket=b.label, x=float(b.centroid[1]), y=float(b.centroid[0]),
            alan=float(b.area), maske=(etiketler == b.label),
        ))
    return nesneler, etiketler


def _iou(a: np.ndarray, b: np.ndarray) -> float:
    kesisim = np.logical_and(a, b).sum()
    if kesisim == 0:
        return 0.0
    return float(kesisim) / float(np.logical_or(a, b).sum())


# --------------------------------------------------------------------------- #
# Yerleşik eşleyici
# --------------------------------------------------------------------------- #
def _yerlesik_takip(
    kare_nesne: list[list[_Nesne]], zamanlar: list[float]
) -> tuple[list[Iz], list[dict]]:
    from scipy.optimize import linear_sum_assignment

    izler: dict[int, Iz] = {}
    bolunmeler: list[dict] = []
    sonraki_id = 1
    # kare 0
    onceki_map: dict[int, int] = {}  # nesne indeksi -> iz id
    for i, nes in enumerate(kare_nesne[0]):
        izler[sonraki_id] = Iz(sonraki_id, None,
                               [IzNoktasi(0, zamanlar[0], nes.x, nes.y, nes.alan)])
        onceki_map[i] = sonraki_id
        sonraki_id += 1

    for k in range(1, len(kare_nesne)):
        onceki, simdi = kare_nesne[k - 1], kare_nesne[k]
        if not simdi:
            onceki_map = {}
            continue
        if not onceki:
            onceki_map = {}
            for j, nes in enumerate(simdi):
                izler[sonraki_id] = Iz(sonraki_id, None,
                                       [IzNoktasi(k, zamanlar[k], nes.x, nes.y, nes.alan)])
                onceki_map[j] = sonraki_id
                sonraki_id += 1
            continue

        maliyet = np.ones((len(onceki), len(simdi)), dtype=np.float32)
        for a, o in enumerate(onceki):
            for b, s in enumerate(simdi):
                d = float(np.hypot(o.x - s.x, o.y - s.y))
                if d > MAKS_MERKEZ_UZAKLIK:
                    continue  # maliyet = 1 (imkânsız)
                iou = _iou(o.maske, s.maske)
                alan_farki = abs(o.alan - s.alan) / max(o.alan, s.alan, 1.0)
                # Birleşik maliyet: konum + örtüşme + alan tutarlılığı
                maliyet[a, b] = (
                    0.55 * min(1.0, d / MAKS_MERKEZ_UZAKLIK)
                    + 0.35 * (1.0 - iou)
                    + 0.10 * min(1.0, alan_farki)
                )

        satir, sutun = linear_sum_assignment(maliyet)
        eslesen_simdi: dict[int, int] = {}   # simdi idx -> onceki idx
        yeni_map: dict[int, int] = {}
        for a, b in zip(satir, sutun):
            if maliyet[a, b] <= ESLESME_ESIGI:
                eslesen_simdi[b] = a

        # Bölünme: bir önceki nesneye iyi örtüşen 2+ simdi nesnesi
        onceki_cocuklar: dict[int, list[int]] = {}
        for b, s in enumerate(simdi):
            if b in eslesen_simdi:
                continue
            en_iyi_a, en_iyi_iou = None, 0.25
            for a, o in enumerate(onceki):
                iou = _iou(o.maske, s.maske)
                if iou > en_iyi_iou:
                    en_iyi_a, en_iyi_iou = a, iou
            if en_iyi_a is not None:
                onceki_cocuklar.setdefault(en_iyi_a, []).append(b)

        for b, s in enumerate(simdi):
            if b in eslesen_simdi:
                a = eslesen_simdi[b]
                iz_id = onceki_map.get(a)
                if iz_id is None:
                    iz_id = sonraki_id
                    izler[iz_id] = Iz(iz_id, None, [])
                    sonraki_id += 1
                izler[iz_id].noktalar.append(
                    IzNoktasi(k, zamanlar[k], s.x, s.y, s.alan))
                yeni_map[b] = iz_id
            else:
                # bölünme çocuğu mu?
                ebeveyn_a = next((a for a, cs in onceki_cocuklar.items() if b in cs and len(cs) >= 2), None)
                parent_id = onceki_map.get(ebeveyn_a) if ebeveyn_a is not None else None
                izler[sonraki_id] = Iz(
                    sonraki_id, parent_id,
                    [IzNoktasi(k, zamanlar[k], s.x, s.y, s.alan)])
                if parent_id is not None and not any(
                    x["kare"] == k and x["parent"] == parent_id for x in bolunmeler
                ):
                    bolunmeler.append({"kare": k, "zaman_sn": zamanlar[k],
                                       "parent": parent_id, "cocuklar": []})
                if parent_id is not None:
                    for bl in bolunmeler:
                        if bl["kare"] == k and bl["parent"] == parent_id:
                            bl["cocuklar"].append(sonraki_id)
                yeni_map[b] = sonraki_id
                sonraki_id += 1

        onceki_map = yeni_map

    return list(izler.values()), bolunmeler


# --------------------------------------------------------------------------- #
# trackastra (opsiyonel)
# --------------------------------------------------------------------------- #
def _trackastra_takip(
    kareler_rgb: list[np.ndarray], etiket_yiginlari: list[np.ndarray], zamanlar: list[float]
) -> tuple[list[Iz], list[dict]] | None:
    try:
        import torch
        from trackastra.model import Trackastra
    except Exception:
        return None
    try:
        from trackastra.tracking import graph_to_napari_tracks

        imgs = np.stack([cv2.cvtColor(k, cv2.COLOR_RGB2GRAY) for k in kareler_rgb]).astype(np.float32)
        masks = np.stack(etiket_yiginlari).astype(np.int32)
        model = Trackastra.from_pretrained("general_2d", device="cpu")
        cikti = model.track(imgs, masks, mode="greedy")
        G = cikti[0] if isinstance(cikti, tuple) else cikti
        if hasattr(G, "tracking_graph"):
            G = G.tracking_graph
        if not hasattr(G, "nodes"):
            return None

        # napari izleri: satır = [iz_id, t, y, x]; ebeveyn bilgisi ayrı döner
        veri = graph_to_napari_tracks(G)
        satirlar = veri[0] if isinstance(veri, tuple) else veri
        ebeveyn_tablo = {}
        if isinstance(veri, tuple) and len(veri) >= 2 and isinstance(veri[1], dict):
            ebeveyn_tablo = veri[1]

        izler: dict[int, Iz] = {}
        alan_arama = _alan_haritalari(etiket_yiginlari)
        for satir in satirlar:
            iz_id, t, y, x = int(satir[0]), int(satir[1]), float(satir[2]), float(satir[3])
            izler.setdefault(iz_id, Iz(iz_id, None, []))
            alan = alan_arama(t, y, x)
            izler[iz_id].noktalar.append(
                IzNoktasi(t, zamanlar[t] if t < len(zamanlar) else float(t), x, y, alan))
        for iid, iz in izler.items():
            iz.noktalar.sort(key=lambda p: p.kare)
            eb = ebeveyn_tablo.get(iid)
            if isinstance(eb, (list, tuple)) and eb:
                iz.parent_id = int(eb[0])
            elif isinstance(eb, int) and eb != iid:
                iz.parent_id = eb

        izler_list = [iz for iz in izler.values() if iz.noktalar]
        if not izler_list:
            return None
        # Gerçek bölünme = bir ebeveynin 2+ çocuğu (tek çocuk yalnızca iz kimliği
        # değişimidir, bölünme değil).
        cocuk_gruplari: dict[int, list[Iz]] = {}
        for iz in izler_list:
            if iz.parent_id:
                cocuk_gruplari.setdefault(iz.parent_id, []).append(iz)
        bolunmeler = []
        for ebeveyn, cocuklar in cocuk_gruplari.items():
            if len(cocuklar) >= 2:
                k = min(c.baslangic_kare for c in cocuklar)
                bolunmeler.append({
                    "kare": k,
                    "zaman_sn": zamanlar[k] if k < len(zamanlar) else float(k),
                    "parent": ebeveyn, "cocuklar": [c.id for c in cocuklar],
                })
            else:
                cocuklar[0].parent_id = None  # sahte bölünme bağını temizle
        return izler_list, bolunmeler
    except Exception as e:  # pragma: no cover
        log.warning("trackastra çalıştırılamadı (%s). Yerleşik takibe düşülüyor.", e)
        return None


def _alan_haritalari(etiket_yiginlari: list[np.ndarray]):
    """(t, y, x) -> o pikseldeki nesnenin alanı (yaklaşık)."""
    from skimage.measure import regionprops

    kare_alan: list[dict[int, float]] = []
    for et in etiket_yiginlari:
        kare_alan.append({b.label: float(b.area) for b in regionprops(et)})

    def bul(t: int, y: float, x: float) -> float:
        if not (0 <= t < len(etiket_yiginlari)):
            return 0.0
        et = etiket_yiginlari[t]
        yi, xi = int(np.clip(y, 0, et.shape[0] - 1)), int(np.clip(x, 0, et.shape[1] - 1))
        return kare_alan[t].get(int(et[yi, xi]), 0.0)

    return bul


# --------------------------------------------------------------------------- #
# Kaplama görselleri
# --------------------------------------------------------------------------- #
def _kaplama_kareler(
    kareler_rgb: list[np.ndarray], izler: list[Iz], cikti_dizini: Path
) -> tuple[list[str], str | None]:
    from app.utils.dosya import rel

    ayar = ayarlari_al()
    kare_izleri: dict[int, list[tuple[int, IzNoktasi]]] = {}
    for iz in izler:
        for p in iz.noktalar:
            kare_izleri.setdefault(p.kare, []).append((iz.id, p))

    from app.utils.dosya import gorsel_yaz

    yollar = []
    h, w = kareler_rgb[0].shape[:2]
    vyol = cikti_dizini / f"takip_{benzersiz_ad('.mp4')}"
    # Tarayıcı uyumluluğu için önce H.264 (avc1) dene, olmazsa mp4v.
    yaz = cv2.VideoWriter(str(vyol), cv2.VideoWriter_fourcc(*"avc1"), 6, (w, h))
    if not yaz.isOpened():
        yaz = cv2.VideoWriter(str(vyol), cv2.VideoWriter_fourcc(*"mp4v"), 6, (w, h))
    kapli_kareler = []
    for i, rgb in enumerate(kareler_rgb):
        g = rgb.copy()
        for iz_id, p in kare_izleri.get(i, []):
            renk = PALET[iz_id % len(PALET)]
            cv2.circle(g, (int(p.x), int(p.y)), 7, renk, 2)
            cv2.putText(g, str(iz_id), (int(p.x) + 7, int(p.y) - 7),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, renk, 1, cv2.LINE_AA)
        for iz in izler:
            gecmis = [p for p in iz.noktalar if p.kare <= i][-8:]
            if len(gecmis) >= 2:
                renk = PALET[iz.id % len(PALET)]
                pts = np.array([[int(p.x), int(p.y)] for p in gecmis], np.int32)
                cv2.polylines(g, [pts], False, renk, 1, cv2.LINE_AA)
        cv2.rectangle(g, (0, 0), (w, 22), (20, 20, 20), -1)
        cv2.putText(g, f"Kare {i} - iz: {len(kare_izleri.get(i, []))}",
                    (8, 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
        yaz.write(cv2.cvtColor(g, cv2.COLOR_RGB2BGR))
        kapli_kareler.append(g)
        if i < 6:
            yollar.append(rel(gorsel_yaz(g, cikti_dizini, on_ek=f"takip_kare{i:02d}_"),
                              ayar.veri_dizini))
    yaz.release()

    # Tarayıcıda güvenilir oynatma için animasyonlu GIF (inline gösterim).
    gif_yol = None
    try:
        from PIL import Image

        imgs = [Image.fromarray(cv2.resize(k, (min(w, 480), int(h * min(w, 480) / w))))
                for k in kapli_kareler]
        gp = cikti_dizini / f"takip_{benzersiz_ad('.gif')}"
        imgs[0].save(gp, save_all=True, append_images=imgs[1:], duration=180,
                     loop=0, optimize=True)
        gif_yol = rel(gp, ayar.veri_dizini)
    except Exception as e:  # pragma: no cover
        log.warning("Takip GIF üretilemedi: %s", e)

    return yollar, rel(vyol, ayar.veri_dizini), gif_yol


def _grafik(izler: list[Iz], kare_sayisi: int, bolunmeler: list[dict],
            cikti_dizini: Path) -> str | None:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    from app.utils.dosya import rel

    sayim = [0] * kare_sayisi
    for iz in izler:
        for p in iz.noktalar:
            if 0 <= p.kare < kare_sayisi:
                sayim[p.kare] += 1
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 3.2))
    ax1.plot(range(kare_sayisi), sayim, "-o", color="#0891b2", ms=3)
    for bl in bolunmeler:
        ax1.axvline(bl["kare"], color="#d97706", ls="--", lw=0.8)
    ax1.set_title("Kare başına iz sayısı"); ax1.set_xlabel("kare"); ax1.grid(alpha=.3)
    uzunluklar = [iz.sure_kare for iz in izler]
    ax2.hist(uzunluklar, bins=min(15, max(3, len(set(uzunluklar)))), color="#0e7490")
    ax2.set_title("İz uzunluğu dağılımı (kare)"); ax2.grid(alpha=.3)
    yol = cikti_dizini / f"takip_grafik_{benzersiz_ad('.png')}"
    fig.savefig(yol, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return rel(yol, ayarlari_al().veri_dizini)


# --------------------------------------------------------------------------- #
# Orkestrasyon
# --------------------------------------------------------------------------- #
def takip_analiz(yol: str | Path, *, aralik_sn: float = 1.0,
                 dosya_adi: str | None = None) -> dict:
    ayar = ayarlari_al()
    yol = Path(yol)
    dosya_adi = dosya_adi or yol.name
    cikti = ayar.cikti_dizini
    cikti.mkdir(parents=True, exist_ok=True)

    ham_kareler = _kareler(yol, aralik_sn)
    if len(ham_kareler) < 2:
        raise ValueError("Takip için en az 2 kare gerekir.")
    zamanlar = [t for _, t, _ in ham_kareler]
    kareler_rgb = [k for _, _, k in ham_kareler]

    kare_nesne: list[list[_Nesne]] = []
    etiket_yiginlari: list[np.ndarray] = []
    for rgb in kareler_rgb:
        nesneler, etiketler = _kare_nesneleri(rgb, ayar.omnipose_model)
        kare_nesne.append(nesneler)
        etiket_yiginlari.append(etiketler)

    yontem = "yerlesik-iou"
    sonuc = _trackastra_takip(kareler_rgb, etiket_yiginlari, zamanlar)
    if sonuc is not None:
        izler, bolunmeler = sonuc
        yontem = "trackastra"
    else:
        izler, bolunmeler = _yerlesik_takip(kare_nesne, zamanlar)

    izler = [iz for iz in izler if len(iz.noktalar) >= 1]
    ham_iz_sayisi = len(izler)

    # Yöntemden bağımsız bölünme çıkarımı: 0. kareden sonra doğan bir iz,
    # doğum anında başka bir izin son konumuna ~28 px yakınsa bölünme adayıdır.
    _ID = {iz.id: iz for iz in izler}
    for iz in izler:
        if iz.parent_id or iz.baslangic_kare == 0 or len(iz.noktalar) < 3:
            continue
        bk = iz.baslangic_kare
        bp = iz.noktalar[0]
        en_iyi, en_yakin = None, 30.0
        for aday in izler:
            if aday.id == iz.id:
                continue
            komsu = next((p for p in aday.noktalar if p.kare in (bk - 1, bk)), None)
            if komsu is None:
                continue
            dd = float(np.hypot(komsu.x - bp.x, komsu.y - bp.y))
            if dd < en_yakin:
                en_iyi, en_yakin = aday, dd
        if en_iyi is not None:
            iz.parent_id = en_iyi.id
            bolunmeler.append({
                "kare": bk, "zaman_sn": bp.zaman_sn,
                "parent": en_iyi.id, "cocuklar": [en_iyi.id, iz.id],
            })
    # "Anlamlı iz" = en az 3 kare süren; segmentasyon gürültüsünden gelen
    # kısa parçalar başlık istatistiklerine katılmaz (hepsi JSON'da kalır).
    anlamli = [iz for iz in izler if iz.sure_kare >= 3]
    anlamli_id = {iz.id for iz in anlamli}
    # Sadece iki çocuğu da anlamlı olan bölünmeleri say
    bolunmeler = [
        b for b in bolunmeler
        if sum(1 for c in b["cocuklar"] if c in anlamli_id) >= 2
    ]

    kaplama, video, gif = _kaplama_kareler(kareler_rgb, anlamli or izler, cikti)
    grafik = _grafik(anlamli or izler, len(kareler_rgb), bolunmeler, cikti)

    ilk_sayi = len(kare_nesne[0])
    son_sayi = len(kare_nesne[-1])
    uzun_izler = [iz for iz in anlamli if iz.sure_kare >= 2]
    aciklama = (
        f"{len(kareler_rgb)} kare {aralik_sn:g} sn aralıkla analiz edildi. "
        f"{len(anlamli)} anlamlı iz izlendi (3+ kare süren). "
        f"Hücre sayısı ilk karede {ilk_sayi}, son karede {son_sayi}. "
        f"{len(bolunmeler)} bölünme olayı tespit edildi. "
        f"Eşleme yöntemi: {yontem}. "
    )
    if son_sayi < ilk_sayi * 0.6:
        aciklama += "Hücre sayısında belirgin düşüş var; aktivite kaybı olabilir. "
    elif son_sayi > ilk_sayi * 1.4:
        aciklama += "Hücre sayısı artıyor; aktif üreme gözleniyor. "

    izler_json = []
    for iz in sorted(izler, key=lambda z: z.id):
        izler_json.append({
            "id": iz.id, "parent_id": iz.parent_id,
            "baslangic_kare": iz.baslangic_kare, "bitis_kare": iz.bitis_kare,
            "sure_kare": iz.sure_kare,
            "noktalar": [{"kare": p.kare, "zaman_sn": p.zaman_sn,
                          "x": round(p.x, 1), "y": round(p.y, 1),
                          "alan": round(p.alan, 1)} for p in iz.noktalar],
        })

    zaman_serisi = []
    for i in range(len(kareler_rgb)):
        zaman_serisi.append({
            "kare": i, "zaman_sn": zamanlar[i],
            "hucre_sayisi": len(kare_nesne[i]),
            "aktif_iz": sum(1 for iz in anlamli
                            if iz.baslangic_kare <= i <= iz.bitis_kare),
        })

    from app.utils.dosya import rel

    d = {
        "dosya_adi": dosya_adi,
        "kare_sayisi": len(kareler_rgb),
        "kare_araligi_sn": aralik_sn,
        "yontem": yontem,
        "iz_sayisi": len(anlamli),
        "ham_iz_parcasi": ham_iz_sayisi,
        "uzun_iz_sayisi": len(uzun_izler),
        "bolunme_sayisi": len(bolunmeler),
        "ilk_kare_hucre": ilk_sayi,
        "son_kare_hucre": son_sayi,
        "kaplama_kareler": kaplama,
        "kaplama_video": video,
        "kaplama_gif": gif,
        "grafik": grafik,
        "zaman_serisi": zaman_serisi,
        "izler": izler_json,
        "bolunmeler": bolunmeler,
        "aciklama": aciklama.strip(),
    }

    # CSV + JSON
    csv_yol = cikti / f"takip_izler_{benzersiz_ad('.csv')}"
    with csv_yol.open("w", encoding="utf-8") as f:
        f.write("iz_id,parent_id,kare,zaman_sn,x,y,alan\n")
        for iz in izler_json:
            for p in iz["noktalar"]:
                f.write(f"{iz['id']},{iz['parent_id'] or ''},{p['kare']},"
                        f"{p['zaman_sn']},{p['x']},{p['y']},{p['alan']}\n")
    d["csv_rapor"] = rel(csv_yol, ayar.veri_dizini)

    json_yol = cikti / f"takip_sonuc_{benzersiz_ad('.json')}"
    json_yol.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
    d["json_rapor"] = rel(json_yol, ayar.veri_dizini)
    return d
