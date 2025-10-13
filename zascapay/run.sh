#!/bin/bash
set -e
# ===============================
# 1️⃣  Cài đặt gói hệ thống cần thiết
# ===============================
echo "📦 Installing system packages..."
apt update -y
apt install -y pkg-config libmysqlclient-dev build-essential gunicorn

# ===============================
# 2️⃣  Cài Python dependencies
# ===============================
echo "🐍 Installing Python dependencies..."
if [ -f requirements.txt ]; then
    pip install -r requirements.txt
else
    echo "⚠️  requirements.txt not found!"
fi


# ===============================
# 3️⃣  Apply migrations
# ===============================
echo "🗃️ Applying Django migrations..."
cd "$(pwd)/zascapay"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

#echo "🔥 Starting  server..."
#python runserver.py