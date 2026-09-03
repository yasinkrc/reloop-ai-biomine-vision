#!/usr/bin/env bash
# BioMine Vision — yerel kurulum betiği (Docker'sız).
# CPU veya CUDA'yı otomatik algılar, bağımlılıkları kurar, örnek veri üretir,
# DEMO modeli eğitir ve veritabanını hazırlar.
set -euo pipefail

KOK="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$KOK"

PY="${PYTHON:-python3}"
VENV="${VENV_DIZINI:-.venv}"
EGIT_MODEL="${EGIT_MODEL:-1}"
KUR_OMNIPOSE="${KUR_OMNIPOSE:-0}"

echo "==> Python: $($PY --version)"
if [ ! -d "$VENV" ]; then
  echo "==> Sanal ortam oluşturuluyor: $VENV"
  "$PY" -m venv "$VENV"
fi
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel

# --- PyTorch: CUDA var mı? ---
if command -v nvidia-smi >/dev/null 2>&1; then
  echo "==> NVIDIA GPU bulundu — CUDA (cu121) tekerlekleri kuruluyor"
  pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cu121
else
  echo "==> GPU yok — CPU PyTorch kuruluyor"
  pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
fi

echo "==> Diğer bağımlılıklar"
grep -vE '^\s*(torch|torchvision)\b' requirements.txt > /tmp/biomine_reqs.txt
pip install -r /tmp/biomine_reqs.txt

if [ "$KUR_OMNIPOSE" = "1" ]; then
  echo "==> Omnipose kuruluyor (opsiyonel)"
  pip install omnipose || echo "!! Omnipose kurulamadı — klasik segmentasyona düşülecek"
fi

echo "==> Örnek veri + DEMO model"
python scripts/ornek_veri_uret.py --sinif_basi 36
if [ "$EGIT_MODEL" = "1" ]; then
  # Hızlı DEMO eğitimi: omurga dondurulur, yalnızca sınıflandırma kafası eğitilir.
  # Tam eğitim için:  python scripts/model_egit.py --epok 12
  python scripts/model_egit.py --epok 6 --dondur --boyut 224
fi

echo "==> Örnek genom + zaman serisi (CRISPR-Cas ve Hücre Takibi demoları)"
python scripts/ornek_genom_uret.py || echo "!! örnek genom üretilemedi"
python scripts/ornek_takip_uret.py || echo "!! örnek zaman serisi üretilemedi"

# Opsiyonel: genom benzerliği için skani (yoksa tür ataması atlanır)
if [ "${KUR_SKANI:-0}" = "1" ] && command -v brew >/dev/null 2>&1; then
  echo "==> skani / hmmer / prodigal / mmseqs2 / mummer kuruluyor (opsiyonel)"
  brew install skani hmmer prodigal mmseqs2 mummer libomp || echo "!! bio araçları kurulamadı"
fi
# Opsiyonel: gelişmiş Cas tiplemesi / transformer takibi
if [ "${KUR_BIO_ILERI:-0}" = "1" ]; then
  pip install cctyper trackastra || echo "!! cctyper/trackastra kurulamadı"
fi

echo "==> Veritabanı hazırlanıyor"
python -c "from app.database import veritabanini_hazirla; veritabanini_hazirla(); print('veritabanı hazır')"

echo "==> Hızlı uçtan uca test"
python scripts/demo.py || echo "!! demo.py hata verdi, logları inceleyin"

cat <<'EOF'

Kurulum tamam.
  Sunucuyu başlat:  source .venv/bin/activate && uvicorn app.main:app --reload
  API dokümanı:     http://localhost:8000/docs
  Sağlık kontrolü:  http://localhost:8000/api/saglik
EOF
