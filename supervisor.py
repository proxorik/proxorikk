#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import subprocess
import signal
import sys
import logging
from datetime import datetime
import threading
import requests

# Настройка логирования
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"supervisor_{datetime.now().strftime('%Y%m%d')}.log")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("supervisor")

# Константы
CHECK_INTERVAL = 60  # Интервал проверки в секундах
KEEP_ALIVE_URL = "http://localhost:8080/health"
MAX_RESTARTS = 1000  # Максимальное число перезапусков
BOT_SCRIPT = "bot.py"  # Имя основного скрипта бота
RESTART_TIMEOUT = 5  # Пауза между перезапусками в секундах

# Глобальные переменные
process = None
restart_count = 0
last_restart_time = None
running = True

def signal_handler(sig, frame):
    """Обработчик сигналов для корректного завершения"""
    global running, process
    logger.info("Получен сигнал завершения. Остановка супервизора...")
    running = False
    
    if process and process.poll() is None:
        try:
            logger.info("Остановка процесса бота...")
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            logger.warning("Бот не остановился в течение таймаута. Принудительное завершение...")
            process.kill()
    
    sys.exit(0)

def start_bot():
    """Запустить бота как отдельный процесс"""
    global process, last_restart_time
    
    try:
        logger.info("Запуск бота...")
        
        # Используем тот же интерпретатор Python, что запустил супервизора
        python_path = sys.executable
        
        # Запускаем бота как отдельный процесс
        process = subprocess.Popen(
            [python_path, BOT_SCRIPT],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,
            universal_newlines=True
        )
        
        last_restart_time = datetime.now()
        logger.info(f"Бот запущен с PID: {process.pid}")
        
        # Запускаем поток для мониторинга вывода бота
        threading.Thread(target=monitor_bot_output, daemon=True).start()
        
        return True
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {str(e)}")
        return False

def monitor_bot_output():
    """Мониторинг и логирование вывода процесса бота"""
    global process
    
    if not process:
        return
    
    for line in process.stdout:
        logger.info(f"BOT: {line.strip()}")

def check_bot_status():
    """Проверка статуса бота"""
    global process, restart_count
    
    # Проверка процесса
    if process is None or process.poll() is not None:
        logger.warning("Процесс бота не запущен или завершился. Перезапуск...")
        restart_count += 1
        return False
    
    # Проверка веб-сервера (keep-alive)
    try:
        response = requests.get(KEEP_ALIVE_URL, timeout=5)
        if response.status_code != 200:
            logger.warning(f"Keep-alive вернул некорректный статус: {response.status_code}. Перезапуск...")
            restart_count += 1
            return False
    except requests.RequestException as e:
        logger.warning(f"Ошибка при проверке keep-alive: {str(e)}. Перезапуск...")
        restart_count += 1
        return False
    
    # Все проверки пройдены
    return True

def stop_bot():
    """Остановить процесс бота, если он запущен"""
    global process
    
    if process and process.poll() is None:
        try:
            logger.info("Остановка процесса бота...")
            process.send_signal(signal.SIGTERM)
            process.wait(timeout=5)
            logger.info("Процесс бота успешно остановлен")
        except subprocess.TimeoutExpired:
            logger.warning("Бот не остановился в течение таймаута. Принудительное завершение...")
            process.kill()
        
        process = None

def print_status():
    """Вывод статуса супервизора"""
    global restart_count, last_restart_time
    
    uptime = None
    if last_restart_time:
        uptime = datetime.now() - last_restart_time
    
    status = [
        "=" * 50,
        "СТАТУС СУПЕРВИЗОРА",
        "=" * 50,
        f"Бот запущен: {'Да' if process and process.poll() is None else 'Нет'}",
        f"PID бота: {process.pid if process and process.poll() is None else 'N/A'}",
        f"Количество перезапусков: {restart_count}",
        f"Последний перезапуск: {last_restart_time.strftime('%Y-%m-%d %H:%M:%S') if last_restart_time else 'Никогда'}",
        f"Время работы: {str(uptime).split('.')[0] if uptime else 'N/A'}",
        "=" * 50
    ]
    
    for line in status:
        logger.info(line)

def main():
    global running, restart_count
    
    # Регистрируем обработчики сигналов для корректного завершения
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Супервизор запущен")
    
    # Первый запуск бота
    if not start_bot():
        logger.critical("Не удалось запустить бота. Выход...")
        return
    
    # Основной цикл супервизора
    try:
        while running and restart_count < MAX_RESTARTS:
            time.sleep(CHECK_INTERVAL)
            
            # Вывод текущего статуса
            print_status()
            
            # Проверка статуса бота
            if not check_bot_status():
                logger.warning(f"Перезапуск #{restart_count} из {MAX_RESTARTS}...")
                stop_bot()
                time.sleep(RESTART_TIMEOUT)
                if not start_bot():
                    logger.error("Ошибка при перезапуске бота")
            else:
                logger.info("Проверка статуса: OK")
    
    except Exception as e:
        logger.critical(f"Неожиданная ошибка в супервизоре: {str(e)}")
    finally:
        # Корректное завершение
        logger.info("Завершение работы супервизора")
        stop_bot()

if __name__ == "__main__":
    main()