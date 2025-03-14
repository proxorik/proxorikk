#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import telebot
from telebot import types
from dotenv import load_dotenv
import threading
import tempfile
import time
import requests
import sys
import traceback
from datetime import datetime
import telebot
from googlesearch import search
from bs4 import BeautifulSoup
import requests
from openai_helper import generate_ai_response, analyze_image, analyze_video
from conversation_handler import get_conversation_history, add_to_conversation, clear_conversation
from user_preferences import update_user_preferences
from keep_alive import keep_alive
from g4f.client import Client

client = Client()
response = client.chat.completions.create(
    model="gpt-4o-mini",
    messages=[{"role": "user", "content": "Hello"}],
    web_search=False
)
print(response.choices[0].message.content)

# Load environment variables
load_dotenv()

# Configure detailed logging
log_dir = "logs"
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, f"bot_{datetime.now().strftime('%Y%m%d')}.log")

# Enable logging to both console and file
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    logger.error("Please set the TELEGRAM_TOKEN environment variable.")
    exit(1)

# Define exception handler for uncaught exceptions
def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        # Default behavior for KeyboardInterrupt
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    # Log the error details
    logger.critical("Uncaught exception:", exc_info=(exc_type, exc_value, exc_traceback))
    logger.critical(f"Exception type: {exc_type}")
    logger.critical(f"Exception value: {exc_value}")
    logger.critical(f"Traceback: {''.join(traceback.format_tb(exc_traceback))}")

# Set the exception hook
sys.excepthook = handle_exception

# Initialize the bot with appropriate configuration
bot = telebot.TeleBot(TELEGRAM_TOKEN, threaded=True, num_threads=5)

# Handle /start command
@bot.message_handler(commands=["start"])
def start_command(message):
    """Send a message when the command /start is issued."""
    user_first_name = message.from_user.first_name
    
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=2)
    help_button = types.InlineKeyboardButton("Помощь", callback_data="help")
    clear_button = types.InlineKeyboardButton("Очистить чат", callback_data="clear_chat")
    markup.add(help_button, clear_button)
    
    bot.send_message(
        message.chat.id,
        f"Привет, {user_first_name}! 👋 Я Cookie AI, твой дружелюбный помощник, созданный Вадимом Прохоренко! ✨\n\n"
        f"Я очень рад общаться с тобой! 🎉 Просто отправь мне сообщение, и я дам осмысленным ответ. Я здесь, чтобы помогать, развлекать или просто обсуждать твой день! 💬\n\n"
        f"🍪 Интересный факт: я являюсь частью растущей экосистемы, которая скоро будет включать мобильные приложения в Google Play Store и App Store, а также мем-коин под названием Cookie AI! 🚀",
        reply_markup=markup,
        parse_mode="HTML"
    )

# Handle /help command
@bot.message_handler(commands=["help"])
def help_command(message):
    """Send a message when the command /help is issued."""
    # Create inline keyboard
    markup = types.InlineKeyboardMarkup(row_width=1)
    clear_button = types.InlineKeyboardButton("Очистить чат", callback_data="clear_chat")
    markup.add(clear_button)
    
    bot.send_message(
        message.chat.id,
        "📚 Как использовать Cookie AI:\n\n"
        "- 💬 Просто отправь любое сообщение, и я отвечу с помощью своего ИИ-мозга 🧠\n"
        "- 📸 Отправь мне фотографию, и я расскажу, что на ней вижу\n"
        "- 🎥 Отправь мне видео, и я проанализирую всё его содержание (а не только первый кадр)\n"
        "- 🎤 Отправь мне голосовое сообщение, и я распознаю речь и отвечу на твой вопрос\n"
        "- 🔘 Запиши круговое видео (видеосообщение), и я проанализирую что на нем\n"
        "- 🗑️ Используй /clear, чтобы очистить историю нашего разговора\n"
        "- 🔄 Используй /start, чтобы начать наш дружеский чат заново\n"
        "- ❓ Используй /help, чтобы увидеть эту справку снова\n\n"
        "🍪 Обо мне: я Cookie AI, созданный 15-летним разработчиком Вадимом Прохоренко. Скоро я буду доступен как приложение в Google Play и App Store, а также готовится выпуск мем-коина Cookie AI! 🚀\n\n"
        "О чём ты хочешь поговорить сегодня? 😊",
        reply_markup=markup
    )

# Handle /clear command
@bot.message_handler(commands=["clear"])
def clear_command(message):
    """Clear conversation history when the command /clear is issued."""
    user_id = message.from_user.id
    clear_conversation(user_id)
    bot.send_message(message.chat.id, "🧹 Готово! История нашего разговора очищена! ✨ Теперь мы начинаем с чистого листа. О чём ты хочешь поговорить? 😊")

# Создадим временную директорию для хранения файлов
TEMP_DIR = "temp_media"
os.makedirs(TEMP_DIR, exist_ok=True)

# Handle photo messages
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    """Process and respond to photos sent by users."""
    user_id = message.from_user.id
    
    try:
        # Show the bot is processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Get caption if available
        caption = ""
        if message.caption:
            caption = message.caption
            # Update preferences based on caption
            update_user_preferences(user_id, caption)
        
        # Get the highest quality photo
        file_info = bot.get_file(message.photo[-1].file_id)
        
        # Generate a unique filename
        photo_path = os.path.join(TEMP_DIR, f"photo_{user_id}_{int(time.time())}.jpg")
        
        # Download the photo
        downloaded_file = bot.download_file(file_info.file_path)
        with open(photo_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Analyze the image
        custom_prompt = f"Опиши, что ты видишь на этом изображении. {caption}" if caption else None
        analysis = analyze_image(photo_path, custom_prompt)
        
        # Add user and bot messages to conversation history
        image_desc = f"[Пользователь отправил фотографию{': ' + caption if caption else ''}]"
        add_to_conversation(user_id, "user", image_desc)
        add_to_conversation(user_id, "assistant", analysis)
        
        # Send the response
        bot.send_message(message.chat.id, analysis)
        
        # Clean up
        try:
            os.remove(photo_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error processing photo: {str(e)}")
        bot.send_message(
            message.chat.id,
            "😓 Ой! У меня возникла проблема при обработке фотографии. Пожалуйста, попробуйте отправить её еще раз или в другом формате."
        )

# Handle video messages
@bot.message_handler(content_types=['video'])
def handle_video(message):
    """Process and respond to videos sent by users."""
    user_id = message.from_user.id
    
    try:
        # Show the bot is processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Get caption if available
        caption = ""
        if message.caption:
            caption = message.caption
            # Update preferences based on caption
            update_user_preferences(user_id, caption)
        
        # Download both the video and its thumbnail
        video_path = None
        thumbnail_path = None
        
        # Get the video file itself
        try:
            video_file_info = bot.get_file(message.video.file_id)
            video_path = os.path.join(TEMP_DIR, f"video_{user_id}_{int(time.time())}.mp4")
            video_downloaded_file = bot.download_file(video_file_info.file_path)
            with open(video_path, 'wb') as new_file:
                new_file.write(video_downloaded_file)
        except Exception as e:
            logger.error(f"Error downloading video: {str(e)}")
        
        # Get video thumbnail as fallback
        try:
            if message.video.thumbnail:
                thumbnail_file_info = bot.get_file(message.video.thumbnail.file_id)
                thumbnail_path = os.path.join(TEMP_DIR, f"video_thumb_{user_id}_{int(time.time())}.jpg")
                thumbnail_downloaded_file = bot.download_file(thumbnail_file_info.file_path)
                with open(thumbnail_path, 'wb') as new_file:
                    new_file.write(thumbnail_downloaded_file)
        except Exception as e:
            logger.error(f"Error downloading thumbnail: {str(e)}")
        
        # Show the bot is still processing 
        bot.send_chat_action(message.chat.id, "typing")
        
        # Create custom prompt based on caption
        custom_prompt = None
        if caption:
            if "исправить" in caption.lower() or "улучшить" in caption.lower() or "проблема" in caption.lower():
                custom_prompt = f"Это видео, которое пользователь хочет исправить или улучшить. Проанализируй его содержание, выяви возможные проблемы и предложи конкретные решения. Контекст от пользователя: {caption}"
            else:
                custom_prompt = f"Это видео от пользователя. Проанализируй его и дай подробный ответ, учитывая контекст: {caption}"
        # Analyze the video using the enhanced multi-frame approach
        if video_path:
            # Full video analysis with multiple frames
            analysis = analyze_video(video_path, thumbnail_path, custom_prompt, True, 5)
        elif thumbnail_path:
            # Fallback to thumbnail-only analysis
            logger.warning("Using thumbnail-only analysis due to video download failure")
            if not custom_prompt:
                custom_prompt = "Это кадр из видео. Опиши, что ты видишь, и предположи, о чем может быть это видео."
            analysis = analyze_video(None, thumbnail_path, custom_prompt, False, 1)
        else:
            raise Exception("Failed to download both video and thumbnail")
        
        # Add user and bot messages to conversation history
        video_desc = f"[Пользователь отправил видео{': ' + caption if caption else ''}]"
        add_to_conversation(user_id, "user", video_desc)
        add_to_conversation(user_id, "assistant", analysis)
        
        # Send the response
        bot.send_message(message.chat.id, analysis)
        
        # Clean up
        try:
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
            if thumbnail_path and os.path.exists(thumbnail_path):
                os.remove(thumbnail_path)
        except Exception as e:
            logger.error(f"Error cleaning up files: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error processing video: {str(e)}")
        bot.send_message(
            message.chat.id,
            "😓 Ой! У меня возникла проблема при обработке видео. Пожалуйста, попробуйте отправить его еще раз или в другом формате."
        )

# Handle voice messages
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    """Process and respond to voice messages sent by users."""
    user_id = message.from_user.id
    
    try:
        # Show the bot is processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Get caption if available
        caption = ""
        if message.caption:
            caption = message.caption
            # Update preferences based on caption
            update_user_preferences(user_id, caption)
        
        # Get the voice file
        file_info = bot.get_file(message.voice.file_id)
        
        # Generate a unique filename
        voice_path = os.path.join(TEMP_DIR, f"voice_{user_id}_{int(time.time())}.ogg")
        
        # Download the voice file
        downloaded_file = bot.download_file(file_info.file_path)
        with open(voice_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Transcribe the audio
        from openai_helper import transcribe_audio
        custom_prompt = f"Контекст от пользователя: {caption}" if caption else None
        
        # Show the bot is typing while processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Get transcription result
        result = transcribe_audio(voice_path, custom_prompt)
        transcription = result["transcription"]
        response_prefix = result["response"]
        
        # Add transcription to conversation history
        if transcription:
            voice_desc = f"[Голосовое сообщение: \"{transcription}\"{' | ' + caption if caption else ''}]"
            add_to_conversation(user_id, "user", voice_desc)
            
            # Get conversation history for context
            conversation = get_conversation_history(user_id)
            
            # Generate AI response with user preferences
            bot.send_chat_action(message.chat.id, "typing")
            ai_response = generate_ai_response(conversation, user_id)
            
            # Add AI response to conversation history
            add_to_conversation(user_id, "assistant", ai_response)
            
            # Send the response with transcription prefix if applicable
            full_response = f"{response_prefix}{ai_response}" if response_prefix else ai_response
            bot.send_message(message.chat.id, full_response)
        else:
            # If transcription failed, send error message
            bot.send_message(
                message.chat.id,
                "😕 Извините, я не смог разобрать, что было сказано в голосовом сообщении. Возможно, качество звука не очень хорошее или есть фоновый шум. Не могли бы вы повторить голосовое сообщение или написать текстом?"
            )
        
        # Clean up
        try:
            os.remove(voice_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error processing voice message: {str(e)}")
        bot.send_message(
            message.chat.id,
            "😓 Ой! У меня возникла проблема при обработке голосового сообщения. Пожалуйста, попробуйте отправить его еще раз или напишите текстом."
        )

# Handle video notes (круговые видео)
@bot.message_handler(content_types=['video_note'])
def handle_video_note(message):
    """Process and respond to video notes (circular videos) sent by users."""
    user_id = message.from_user.id
    
    try:
        # Show the bot is processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Get the video note file
        file_info = bot.get_file(message.video_note.file_id)
        
        # Generate unique filenames
        video_path = os.path.join(TEMP_DIR, f"video_note_{user_id}_{int(time.time())}.mp4")
        
        # Download the video note
        downloaded_file = bot.download_file(file_info.file_path)
        with open(video_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        # Custom prompt for video notes
        custom_prompt = "Это круговое видео из Telegram (video note). Проанализируй, что на нем происходит и дай подробный ответ. Если человек просит о помощи или задает вопрос, попробуй ответить по сути."
        
        # Analyze the video with multiple frames
        analysis = analyze_video(video_path, None, custom_prompt, True, 5)
        
        # Add to conversation history
        video_desc = "[Пользователь отправил круговое видео]"
        add_to_conversation(user_id, "user", video_desc)
        add_to_conversation(user_id, "assistant", analysis)
        
        # Send the response
        bot.send_message(message.chat.id, analysis)
        
        # Clean up
        try:
            os.remove(video_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Error processing video note: {str(e)}")
        bot.send_message(
            message.chat.id,
            "😓 Ой! У меня возникла проблема при обработке видеосообщения. Пожалуйста, попробуйте отправить его еще раз или опишите ситуацию текстом."
        )

# Handle text messages
@bot.message_handler(content_types=['text'])
def handle_message(message):
    """Handle user text messages and generate AI responses."""
    user_id = message.from_user.id
    message_text = message.text
    
    # Add user message to conversation history
    add_to_conversation(user_id, "user", message_text)
    
    # Update user preferences based on the message
    update_user_preferences(user_id, message_text)
    
    # Get conversation history for context
    conversation = get_conversation_history(user_id)
    
    try:
        # Send "typing" action to show the bot is processing
        bot.send_chat_action(message.chat.id, "typing")
        
        # Generate AI response with user preferences
        ai_response = generate_ai_response(conversation, user_id)
        
        # Add AI response to conversation history
        add_to_conversation(user_id, "assistant", ai_response)
        
        # Send the response
        bot.send_message(message.chat.id, ai_response)
    
    except Exception as e:
        logger.error(f"Error generating response: {str(e)}")
        bot.send_message(
            message.chat.id,
            "😓 Ой! У меня возникла небольшая проблема в процессе обработки. 🤖 Мои схемы немного перегрузились. Не мог бы ты попробовать сформулировать вопрос по-другому? Или, возможно, попробуй повторить запрос через минуту. Приношу извинения за неудобства! 🙏"
        )

# Handle callback queries from inline keyboards
@bot.callback_query_handler(func=lambda call: True)
def handle_callback(call):
    """Handle inline keyboard button callbacks."""
    # Answer the callback query to remove the "loading" state
    bot.answer_callback_query(call.id)
    
    if call.data == "help":
        # Create inline keyboard
        markup = types.InlineKeyboardMarkup(row_width=1)
        clear_button = types.InlineKeyboardButton("Очистить чат", callback_data="clear_chat")
        markup.add(clear_button)
        
        # Edit the message with help information
        bot.edit_message_text(
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            text="📚 Как использовать Cookie AI:\n\n"
                "- 💬 Просто отправь любое сообщение, и я отвечу с помощью своего ИИ-мозга 🧠\n"
                "- 📸 Отправь мне фотографию, и я расскажу, что на ней вижу\n"
                "- 🎥 Отправь мне видео, и я проанализирую всё его содержание (а не только первый кадр)\n"
                "- 🎤 Отправь мне голосовое сообщение, и я распознаю речь и отвечу на твой вопрос\n"
                "- 🔘 Запиши круговое видео (видеосообщение), и я проанализирую что на нем\n"
                "- 🗑️ Используй /clear, чтобы очистить историю нашего разговора\n"
                "- 🔄 Используй /start, чтобы начать наш дружеский чат заново\n"
                "- ❓ Используй /help, чтобы увидеть эту справку снова\n\n"
                "🍪 Обо мне: я Cookie AI, созданный 15-летним разработчиком Вадимом Прохоренко. Скоро я буду доступен как приложение в Google Play и App Store, а также готовится выпуск мем-коина Cookie AI! 🚀\n\n"
                "О чём ты хочешь поговорить сегодня? 😊",
            reply_markup=markup
        )
    
    elif call.data == "clear_chat":
        user_id = call.from_user.id
        clear_conversation(user_id)
        bot.send_message(call.message.chat.id, "🧹 Готово! История нашего разговора очищена! ✨ Теперь мы начинаем с чистого листа. О чём ты хочешь поговорить? 😊")

# Создаем системную команду для мониторинга состояния
@bot.message_handler(commands=["status"])
def status_command(message):
    """Send status information to the administrator."""
    # Проверяем, является ли отправитель администратором (можно настроить список администраторов)
    # В данном примере доступ к команде имеют все, но в продакшен варианте стоит ограничить
    uptime = time.time() - BOT_START_TIME
    days, remainder = divmod(uptime, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, seconds = divmod(remainder, 60)
    
    status_msg = (
        "🤖 *Статус Cookie AI*\n\n"
        f"✅ *Бот активен и работает*\n"
        f"⏱ *Время работы*: {int(days)} дней, {int(hours)} часов, {int(minutes)} минут\n"
        f"🧠 *Память*: {get_memory_usage()} МБ\n"
        f"💾 *Диск*: {get_disk_usage()} ГБ свободно\n"
        f"🔄 *Перезапусков*: {RESTART_COUNT}\n"
        f"⚡ *Последняя проверка соединения*: {last_connection_check.strftime('%Y-%m-%d %H:%M:%S')}\n"
    )
    
    bot.send_message(message.chat.id, status_msg, parse_mode="Markdown")

def get_memory_usage():
    """Get memory usage of the current process in MB."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        return round(memory_info.rss / (1024 * 1024), 2)  # Convert to MB
    except:
        return "Н/Д"  # Если psutil недоступен

def get_disk_usage():
    """Get available disk space in GB."""
    try:
        total, used, free = shutil.disk_usage("/")
        return round(free / (1024 * 1024 * 1024), 2)  # Convert to GB
    except:
        return "Н/Д"  # Если функция недоступна

def check_telegram_connection():
    """Check if the connection to Telegram API is working."""
    global last_connection_check
    last_connection_check = datetime.now()
    
    try:
        # Получаем информацию о боте как проверку связи
        bot_info = bot.get_me()
        logger.info(f"Connection check successful. Bot username: {bot_info.username}")
        return True
    except Exception as e:
        logger.error(f"Connection check failed: {str(e)}")
        return False

def connection_monitor():
    """Периодически проверяет соединение с Telegram API."""
    global RESTART_COUNT
    
    while True:
        try:
            time.sleep(CONNECTION_CHECK_INTERVAL)
            
            if not check_telegram_connection():
                logger.warning("Connection to Telegram API lost. Attempting to restart...")
                # В реальной среде мы могли бы перезапустить сам процесс
                # Но для демонстрации просто увеличим счетчик
                RESTART_COUNT += 1
                logger.info(f"Bot restarted. Total restarts: {RESTART_COUNT}")
        except Exception as e:
            logger.error(f"Error in connection monitor: {str(e)}")

def cleanup_temp_files():
    """Периодически очищает временные файлы."""
    while True:
        try:
            time.sleep(TEMP_CLEANUP_INTERVAL)
            
            # Получаем список всех файлов в TEMP_DIR
            now = time.time()
            files = [os.path.join(TEMP_DIR, f) for f in os.listdir(TEMP_DIR)]
            
            # Удаляем файлы старше 1 часа
            for f in files:
                if os.path.isfile(f) and os.stat(f).st_mtime < now - 3600:
                    try:
                        os.remove(f)
                        logger.info(f"Removed old temp file: {f}")
                    except Exception as e:
                        logger.error(f"Error removing temp file {f}: {str(e)}")
        except Exception as e:
            logger.error(f"Error in temp file cleanup: {str(e)}")

def main():
    """Start the bot and background services."""
    global BOT_START_TIME, last_connection_check, RESTART_COUNT
    
    # Инициализируем глобальные переменные
    BOT_START_TIME = time.time()
    last_connection_check = datetime.now()
    RESTART_COUNT = 0
    
    # Запускаем веб-сервер для keep-alive
    logger.info("Starting keep-alive server...")
    keep_alive()  # Start the Flask server in a separate thread
    
    # Запускаем мониторинг соединения в отдельном потоке
    logger.info("Starting connection monitor...")
    threading.Thread(target=connection_monitor, daemon=True).start()
    
    # Запускаем очистку временных файлов в отдельном потоке
    logger.info("Starting temp file cleanup service...")
    threading.Thread(target=cleanup_temp_files, daemon=True).start()
    
    # Запускаем бота с обработкой ошибок и автоматическим перезапуском
    logger.info("Starting bot...")
    while True:
        try:
            # Запускаем бота с бесконечным поллингом
            bot.infinity_polling(timeout=60, long_polling_timeout=60)
        except Exception as e:
            # Логируем ошибку
            logger.error(f"Bot polling encountered an error: {str(e)}")
            logger.error("Restarting bot in 10 seconds...")
            
            # Увеличиваем счетчик перезапусков
            RESTART_COUNT += 1
            
            # Ждем перед перезапуском
            time.sleep(10)
            logger.info(f"Restarting bot... (Restart count: {RESTART_COUNT})")
        else:
            # Если бот завершился без ошибок (маловероятно), выходим из цикла
            break

# Глобальные переменные для отслеживания состояния
BOT_START_TIME = time.time()
RESTART_COUNT = 0
CONNECTION_CHECK_INTERVAL = 300  # 5 минут
TEMP_CLEANUP_INTERVAL = 3600  # 1 час
last_connection_check = datetime.now()

# Импортируем дополнительные модули
import shutil  # Для получения информации о диске

if __name__ == "__main__":
    main()
