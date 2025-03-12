FROM python:3.11-slim

# Устанавливаем системные зависимости и обновляем пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    gcc \
    python3-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем сначала только файлы зависимостей
# для лучшего использования кэша Docker
COPY railway-requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r railway-requirements.txt && \
    pip install --no-cache-dir psutil

# Только затем копируем остальные файлы проекта
COPY . .

# Создаем директории для работы приложения
RUN mkdir -p /app/temp_media /app/logs /app/user_data \
    && chmod -R 755 /app/temp_media /app/logs /app/user_data

# Expose port 8080 for the Flask keep-alive server
EXPOSE 8080

# Устанавливаем переменную окружения для Python
ENV PYTHONUNBUFFERED=1

# Запускаем бота
CMD ["python", "bot.py"]