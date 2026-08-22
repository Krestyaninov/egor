#!/bin/bash
set -e

echo "=== 🚀 Деплой проекта Egor Bot (@egor_quapmi_bot) ==="

# Подтягивание последних изменений из Git
if [ -d ".git" ]; then
    echo "📥 Получение обновлений из GitHub..."
    git pull origin main
fi

# Сборка и перезапуск контейнера
echo "🐳 Сборка и запуск Docker-контейнера..."
docker compose down || true
docker compose up -d --build

echo "=== ✅ Деплой успешно завершен! ==="
docker compose ps
