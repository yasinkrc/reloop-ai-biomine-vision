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

## Teknoloji

- **Backend:** Python 3.11, FastAPI, SQLAlchemy, Uvicorn
- **Yapay zeka:** PyTorch 2.5 + torchvision, Omnipose (opsiyonel), OpenCV, scikit-image
- **Frontend:** Next.js 14 (App Router), React 18, TypeScript, Tailwind CSS, Recharts
- **Veritabanı:** SQLite (ön tanımlı) veya PostgreSQL
- **Paketleme:** Docker + Docker Compose (backend + frontend + db)
