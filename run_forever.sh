#!/bin/bash

# Скрипт для поддержания непрерывной работы бота
# Запускает супервизор и перезапускает его при необходимости

LOG_DIR="logs"
mkdir -p "$LOG_DIR"
SUPERVISOR_LOG="$LOG_DIR/run_forever.log"

echo "$(date) - Запуск системы поддержания работы бота" >> "$SUPERVISOR_LOG"

# Функция для запуска супервизора
start_supervisor() {
  echo "$(date) - Запуск супервизора..." >> "$SUPERVISOR_LOG"
  python supervisor.py
  return $?
}

# Функция для очистки старых логов
cleanup_logs() {
  echo "$(date) - Очистка старых логов..." >> "$SUPERVISOR_LOG"
  find "$LOG_DIR" -name "*.log" -type f -mtime +7 -delete
  find "temp_media" -type f -mtime +1 -delete
}

# Основной цикл
while true; do
  echo "$(date) - Проверка и запуск системы" >> "$SUPERVISOR_LOG"
  
  # Очистка старых логов каждые 24 часа
  cleanup_logs
  
  # Запуск супервизора
  start_supervisor
  
  # Если супервизор завершился, записываем это в лог
  EXIT_CODE=$?
  echo "$(date) - Супервизор завершился с кодом: $EXIT_CODE" >> "$SUPERVISOR_LOG"
  
  # Пауза перед перезапуском
  echo "$(date) - Ожидание 30 секунд перед перезапуском..." >> "$SUPERVISOR_LOG"
  sleep 30
done