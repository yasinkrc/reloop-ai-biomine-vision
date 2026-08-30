# BioMine Vision backend — CPU imajı (CUDA için aşağıdaki nota bakın).
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# OpenCV / scikit-image / video için sistem kütüphaneleri
RUN apt-get update && apt-get install -y --no-install-recommends \
    libglib2.0-0 libsm6 libxext6 libxrender1 libgl1 ffmpeg curl \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /uygulama

COPY requirements.txt .
# CPU PyTorch tekerleklerini ayrı indekse yönlendir (imaj boyutunu küçültür)
RUN pip install --upgrade pip wheel \
 && pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu \
 && grep -vE '^\s*(torch|torchvision)\b' requirements.txt > /tmp/reqs.txt \
 && pip install -r /tmp/reqs.txt

COPY . .

# Örnek veri + DEMO modeli imaj içinde üret (yarışma jürisi tek komutla çalıştırabilsin)
RUN python scripts/ornek_veri_uret.py --sinif_basi 24 \
 && python scripts/model_egit.py --epok 6 --dondur --boyut 224 || echo "DEMO model eğitimi atlandı"

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD curl -fsS http://localhost:8000/api/saglik || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

# --- CUDA notu ---
# GPU için ilk pip satırını şununla değiştirin:
#   pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
# ve imajı nvidia/cuda tabanlı bir taban imajla yeniden oluşturun.
