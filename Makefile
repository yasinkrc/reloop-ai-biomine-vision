# BioMine Vision — kısayollar
.PHONY: yardim kurulum backend frontend test demo docker temiz model

yardim:
	@echo "kurulum   - backend sanal ortamı + bağımlılıklar + örnek veri + demo model"
	@echo "backend   - FastAPI sunucusunu başlat (localhost:8000)"
	@echo "frontend  - Next.js geliştirme sunucusu (localhost:3000)"
	@echo "test      - backend birim + API testleri"
	@echo "demo      - sunucusuz uçtan uca demo senaryosu"
	@echo "model     - örnek veri üret + DEMO sınıflandırıcıyı eğit"
	@echo "docker    - tüm sistemi Docker Compose ile ayağa kaldır"
	@echo "temiz     - üretilen veri/model/venv dosyalarını sil"

kurulum:
	cd backend && bash scripts/kurulum.sh

backend:
	cd backend && . .venv/bin/activate && uvicorn app.main:app --reload --port 8000

frontend:
	cd frontend && npm install && npm run dev

test:
	cd backend && . .venv/bin/activate && python -m pytest

demo:
	cd backend && . .venv/bin/activate && python scripts/demo.py

model:
	cd backend && . .venv/bin/activate && python scripts/ornek_veri_uret.py --sinif_basi 60 && python scripts/model_egit.py --epok 6 --dondur --boyut 224

docker:
	docker compose up --build

temiz:
	rm -rf veri modeller backend/.venv backend/ornek_veri/*/ backend/ornek_veri/*.png
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
