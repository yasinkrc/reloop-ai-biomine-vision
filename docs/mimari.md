# BioMine Vision — Sistem Mimarisi

## Genel bakış

```
┌──────────────┐     HTTP/JSON      ┌───────────────────────────────┐
│  Frontend    │  ───────────────▶  │  Backend (FastAPI)            │
│  Next.js 14  │  ◀───────────────  │  /api/analiz, /api/gecmis ... │
│  (React/TS)  │   statik görseller │                               │
└──────────────┘   /veri/*          └───────────────┬───────────────┘
                                                    │
                          ┌─────────────────────────┼─────────────────────────┐
                          ▼                         ▼                         ▼
                 ┌─────────────────┐      ┌───────────────────┐     ┌──────────────────┐
                 │ Ön işleme       │      │ Segmentasyon      │     │ Sınıflandırma    │
                 │ OpenCV / skimage│      │ Omnipose (MIT)    │     │ PyTorch          │
                 │ gürültü, CLAHE  │      │  └ fallback:      │     │ EfficientNetV2   │
                 │ kalite ölçümü   │      │    watershed      │     │ + Grad-CAM       │
                 └────────┬────────┘      └─────────┬─────────┘     └────────┬─────────┘
                          │                        │                        │
                          └───────────┬────────────┴────────────┬───────────┘
                                      ▼                         ▼
                             ┌─────────────────┐       ┌──────────────────┐
                             │ Morfoloji       │       │ Kural motoru     │
                             │ alan/uzunluk/   │       │ uyarılar + risk  │
                             │ şekil, sayım    │       │ (eşikler DB'de)  │
                             └────────┬────────┘       └────────┬─────────┘
                                      └───────────┬─────────────┘
                                                  ▼
                                    ┌──────────────────────────┐
                                    │ Sonuç + kayıt (SQLite/PG)│
                                    │ + PDF/CSV/JSON dışa aktar │
                                    └──────────────────────────┘
```

## Analiz hattı (backend/app/core/hat.py)

1. **Ön işleme** (`on_isleme.py`): görüntü okuma (JPG/PNG/TIFF/16-bit),
   ölçekleme, non-local means gürültü azaltma, LAB uzayında CLAHE kontrast
   iyileştirme, Laplacian varyansı (bulanıklık) ve parlaklık ölçümü.
2. **Segmentasyon** (`segmentasyon.py`): Omnipose `bact_phase_omni` modeli ile
   hücre örneklerinin ayrılması. Omnipose kurulu değilse Otsu + mesafe
   dönüşümü + watershed yedeğine otomatik düşülür. Hangi yöntemin
   kullanıldığı sonuçta raporlanır.
3. **Morfoloji** (`morfoloji.py`): her hücre için alan, majör/minör eksen
   (uzunluk/genişlik), dairesellik, en/boy oranı; çubuk/küresel/filamentli
   sınıflaması; görüntü kaplama oranı ve baskın morfoloji.
4. **Sınıflandırma** (`ml/siniflandirici.py`): EfficientNetV2-S omurgalı
   PyTorch modeli; softmax olasılıkları, ilk 5 sonuç, güven yüzdesi.
   Güven eşiğin altındaysa veya model eğitilmemişse sonuç
   "Bilinmeyen veya desteklenmeyen bakteri" olur.
5. **Grad-CAM** (`grad_cam.py`): son evrişim bloğunda ileri/geri kanca ile
   sınıf-ayrımlı ısı haritası; taban görüntüye JET renk haritasıyla bindirilir.
6. **İşaretleme** (`isaretleme.py`): her hücrenin çevresi kendi renginde
   çizilir, numaralandırılır, üst şeride toplam sayı yazılır.
7. **Kural motoru** (`uyari_motoru.py`): eşiklere göre uyarılar; risk seviyesi
   (normal/dikkat/kritik) ve sade Türkçe açıklama.
8. **Kalıcılık**: `Analiz`/`Numune`/`Ayar` tabloları; görseller `veri/ciktilar/`
   altına yazılır ve `/veri/...` yolundan statik sunulur.

## Kural motoru — üretilen uyarılar

| Kod | Koşul | Seviye |
|---|---|---|
| `goruntu_kalitesi` | Laplacian < `bulaniklik_esik` veya parlaklık < `karanlik_esik` | kritik |
| `yetersiz_numune` | hücre sayısı < `min_hucre_sayisi` | kritik |
| `dusuk_guven` | güven < `guven_uyari` | dikkat |
| `desteklenmeyen_sinif` | güven < `guven_dusuk` veya model eğitilmedi | dikkat |
| `asiri_yogunluk` | kaplama > `asiri_yogunluk_kaplama` veya yoğunluk > `asiri_yogunluk_mp` | dikkat |
| `karisik_kultur` | baskın morfoloji oranı < `baskin_morfoloji_orani` | dikkat |
| `aktivite_kaybi` | ardışık karede düşüş > `aktivite_kaybi_dusus_orani` | kritik |
| `seri_aktivite_kaybi` | seri başı→sonu düşüş > eşik | kritik |

Tüm eşikler `/api/ayarlar` (Yönetim ekranı) üzerinden değiştirilebilir ve
`ayar` tablosunda kalıcıdır.

## CRISPR-Cas analizi (`backend/app/core/genom.py`)

Uç nokta: `POST /api/genom/analiz` · `POST /api/genom/ornek`

1. **Dizi okuma** — Biopython ile FASTA / GenBank / GFF ayrıştırma.
2. **CRISPR bulma** — yerleşik CRT tarzı bulucu: kesin tohum eşleşmesi + esnek
   uzatma; 20–48 bp tekrar, 20–100 bp aralayıcı; ileri + ters şerit; çakışma
   birleştirme. `cctyper` kuruluysa Cas operonu + alt tip için de çağrılır.
3. **Cas adayları** — `prodigal` ORF çağrısı + CRISPR lokuslarına yakınlık.
4. **Tür/suş** — `skani` + paketlenmiş referans genomlarla ANI.
5. **Görselleştirme** — `pyGenomeViz` genom haritası + CRISPR lokus şeması.
6. **Çıktı** — PNG, PDF, HTML, CSV (aralayıcılar), JSON.

Bu modül mevcut görüntü analizi hattına dokunmaz; tamamen eklemedir.

## Hücre takibi (`backend/app/core/takip.py`)

Uç nokta: `POST /api/takip/analiz` · `POST /api/takip/ornek`

1. **Kare çıkarma** — MP4/AVI, çok sayfalı TIFF veya sıralı kare ZIP.
2. **Segmentasyon** — her kare mevcut `segmentasyon` modülüyle.
3. **Eşleme** — `trackastra` kuruluysa transformer modeli; değilse yerleşik
   IoU + merkez uzaklığı + alan tutarlılığı maliyetiyle Macar algoritması (scipy).
4. **Bölünme çıkarımı** — doğum anında ~28 px yakındaki mevcut izle ebeveyn bağı.
5. **Çıktı** — kaplamalı GIF/MP4, kaplamalı kareler, sayım grafiği, CSV (izler),
   JSON (soyağacı).

## Teknoloji

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Uvicorn
- **Yapay zeka:** PyTorch + torchvision (EfficientNetV2, Grad-CAM), Omnipose / Trackastra / CRISPRCasTyper / skani (hepsi opsiyonel, yerleşik yedekli), OpenCV, scikit-image, Biopython, pyGenomeViz
- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts
- **Veritabanı:** SQLite (ön tanımlı) veya PostgreSQL
- **Paketleme:** Docker + Docker Compose (backend + frontend + db)
