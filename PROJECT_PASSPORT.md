# Паспорт проекта и инфраструктурный регламент: Egor

---

## 1. Карточка проекта (Project Card)

| Параметр | Значение |
| :--- | :--- |
| **Название проекта** | `Egor` (Аналитик Егор / Quapmi CRM Analyst Bot) |
| **Тип сервиса** | Фоновый Telegram-бот сквозной CRM-аналитики и мониторинга воронки продаж |
| **Основной репозиторий** | `https://github.com/Krestyaninov/egor.git` (или `git@github.com:Krestyaninov/egor.git`) |
| **Прод-сервер (IP)** | `147.45.211.75` (Ubuntu 22.04 LTS) |
| **Рабочая директория на сервере** | `/opt/projects/egor` |
| **Имя Docker-контейнера** | `egor-bot` |
| **Изолированная Docker-сеть** | `egor_default` (Bridge) |
| **Используемый стек** | Python 3.11, aiogram 3.22, APScheduler 3.11, aiohttp, Bitrix24 REST API, Docker, Docker Compose |

---

## 2. Архитектура размещения на сервере

```text
/opt/projects/
├── fabrica/                     # Проект 1: Fabrica Bot
│   └── ...
│
├── egor/                        # Проект 2: Аналитик Егор (Egor Bot)
│   ├── .git/                    # Git репозиторий (origin main)
│   ├── .env                     # Секреты (токен бота, вебхук Битрикс24)
│   ├── .env.example             # Шаблон переменных
│   ├── Dockerfile               # Инструкция сборки контейнера
│   ├── docker-compose.yml       # Конфигурация запуска сервиса
│   ├── deploy.sh                # Скрипт атомарного деплоя в 1 команду
│   ├── requirements.txt         # Зависимости Python
│   ├── config.py                # Конфигурация и маппинг стадий воронки
│   ├── b24_client.py            # Асинхронный клиент Битрикс24
│   ├── analytics.py             # Сквозной расчет воронки, маржи и отказов
│   ├── handlers.py              # Интерактивные меню и команды Telegram
│   ├── bot.py                   # Точка входа, планировщик и опросник Telegram
│   └── PROJECT_PASSPORT.md      # Паспорт проекта
```

---

## 3. Переменные окружения (`.env`)

Файл `.env` хранится строго на сервере и в `.gitignore`.

```ini
# Bitrix24 Webhook URL
BITRIX_WEBHOOK_URL=https://portal.appmistore.ru/rest/20319/nt9sw7bwjdb9em29/

# Telegram Bot Token (Аналитик Егор - @egor_quapmi_bot)
TELEGRAM_BOT_TOKEN=8627957133:AAE4GvYxXcj1oL_BAAhIGruLq4AeJXONqJg

# Main Catalog IBlock ID
CATALOG_IBLOCK_ID=11
```

---

## 4. Шпаргалка команд управления проектом

Все команды выполняются в директории проекта: `cd /opt/projects/egor`

### 4.1. Развертывание и обновление (Деплой)
```bash
# Обновить код из Git и пересобрать контейнер
./deploy.sh

# Либо вручную:
git pull origin main
docker compose up -d --build
```

### 4.2. Мониторинг и логи
```bash
# Просмотр статуса контейнера
docker compose ps

# Просмотр логов в реальном времени (live)
docker compose logs -f --tail=50

# Просмотр логов конкретного сервиса
docker logs -f egor-bot
```

### 4.3. Управление жизненным циклом
```bash
# Перезапуск сервиса
docker compose restart

# Остановка сервиса
docker compose stop

# Полная остановка и удаление контейнера
docker compose down

# Вход внутрь контейнера (для отладки)
docker exec -it egor-bot /bin/bash
```
