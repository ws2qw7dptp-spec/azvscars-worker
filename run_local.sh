#!/bin/bash
echo "AZvsCars Yerli Başlatma Skripti"

# Check if .env exists
if [ ! -f .env ]; then
    echo "❌ XƏTA: .env faylı tapılmadı! Zəhmət olmasa Render-dəki Environment Variable-ları bura kopyalayın."
    exit 1
fi

# Create venv if not exists
if [ ! -d "venv" ]; then
    echo "Virtual mühit (venv) yaradılır..."
    python3 -m venv venv
fi

# Activate venv
source venv/bin/activate

# Install requirements
echo "Kitabxanalar yüklənir..."
pip install -r requirements.txt

# Run app
echo "🚀 Server başladılır... http://127.0.0.1:5000 ünvanına daxil olun"
export FLASK_ENV=development
python app.py
