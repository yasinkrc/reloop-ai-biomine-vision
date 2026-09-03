# BioMine Vision — Çalışan Demo Senaryosu

Bu belge, jürinin sistemi **birkaç komutla** uçtan uca doğrulaması için
adım adım bir senaryo sunar.

## 0. Ön koşul

```bash
git clone https://github.com/yasinkrc/reloop-ai-biomine-vision.git
cd reloop-ai-biomine-vision
```

## 1. Tek komutla tüm sistem (Docker)

```bash
docker compose up --build
```

Beklenen:
- `backend` servisi örnek veriyi üretir, DEMO modeli eğitir (~birkaç dk) ve
  `healthy` olur.
- <http://localhost:3000> arayüzü açılır, <http://localhost:8000/docs> API dokümanı çalışır.

Doğrulama:
```bash
curl -s http://localhost:8000/api/saglik
# {"durum":"calisiyor", "siniflandirici_egitildi":true, "segmentasyon_yontemi":"...", ...}
```

## 2. Sunucusuz uçtan uca demo (Docker olmadan)

```bash
cd backend
bash scripts/kurulum.sh          # venv + bağımlılık + örnek veri + DEMO model + veritabanı
source .venv/bin/activate
python scripts/demo.py
```

`demo.py` çıktısında görülmesi gerekenler:
1. **Tekli analiz** — segmentasyon yöntemi, hücre sayısı, kaplama oranı, baskın
   morfoloji, tahmin + güven, risk, uyarı listesi, işaretli/Grad-CAM görsel yolları.
2. **Toplu analiz (ZIP)** — 6 görüntü, ortalama hücre sayısı.
3. **Video zaman serisi** — hücre sayısının kare kare düşüşü (aktivite kaybı senaryosu),
   risk seviyesinin `kritik`e yükselmesi.
4. **Rapor** — PDF / CSV / JSON dosyalarının üretildiği yollar.

## 3. Testler

```bash
cd backend && source .venv/bin/activate
python -m pytest -q
# 28 passed
```

## 4. Model yükleme testi

```bash
python - <<'PY'
from app.config import ayarlari_al
from app.ml.siniflandirici import Siniflandirici
a = ayarlari_al()
s = Siniflandirici(model_yolu=a.model_dizini / a.siniflandirici_dosyasi, cihaz="cpu")
print("egitilmedi:", s.egitilmedi, "| giris_boyutu:", s.giris_boyutu, "| sinif:", len(s.siniflar))
PY
# egitilmedi: False | giris_boyutu: 224 | sinif: 8
```

## 5. Arayüz akışları (elle)

| Adım | Sayfa | Beklenen |
|---|---|---|
| Örnek "Çubuk — yoğun" tıkla | `/analiz` | 3 görsel + tahmin + ilk-5 + morfoloji + açıklama |
| ZIP yükle | `/toplu` | özet + kare kare gezinme + PDF/CSV/JSON indir |
| MP4 yükle | `/video` | çizgi grafiği + seri uyarısı + kare seçici |
| "Örnek genom ile dene" | `/crispr` | tür/suş + CRISPR dizileri + aralayıcı sayısı + genom & lokus haritası + PDF/CSV/JSON/HTML |
| "Örnek zaman serisi ile dene" | `/takip` | iz kaplamalı animasyon + sayım grafiği + bölünme olayları + iz tablosu + CSV/JSON |
| Listeyi gör | `/gecmis` | tüm analizler, riskli filtresi, sil |
| İki analiz seç | `/karsilastir` | farklar tablosu + yorum |
| Eşik değiştir | `/ayarlar` | değer kaydedilir, sonraki analizde etkili |
| Tema düğmesi | her sayfa | açık/koyu geçiş, tercih hatırlanır |

## 6. Ekran görüntülerini yeniden üretme

```bash
# backend :8000, frontend :3000 çalışırken
cd frontend
node scripts/ekran-goruntusu.mjs   # docs/ekran-goruntuleri/*.jpg
node scripts/gif-demo.mjs && (cd ../backend && python scripts/gif_birlestir.py)
```
