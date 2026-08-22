FROM python:3.11-slim

WORKDIR /app

# Установка часового пояса Europe/Moscow
ENV TZ=Europe/Moscow
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# Установка зависимостей
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копирование исходного кода
COPY . .

CMD ["python", "bot.py"]
