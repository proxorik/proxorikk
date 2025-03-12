import os
import json
import logging
import base64
import requests
import subprocess
import tempfile
from openai import OpenAI
from knowledge_base import get_knowledge_base
from user_preferences import format_user_preferences_for_prompt

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load OpenAI API key from environment variables
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    logger.error("Please set the OPENAI_API_KEY environment variable.")
    exit(1)

# Initialize the OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Получаем базу знаний
knowledge_base = get_knowledge_base()

def analyze_image(image_path, prompt=None):
    """
    Analyze an image using GPT-4o Vision API.
    
    Args:
        image_path (str): Path to the image file
        prompt (str, optional): A specific prompt to use for image analysis
        
    Returns:
        str: AI-generated description or analysis of the image
    """
    try:
        # Prepare the base64 encoded image
        with open(image_path, "rb") as image_file:
            base64_image = base64.b64encode(image_file.read()).decode("utf-8")
        
        # Default prompt in Russian if none provided
        if not prompt:
            prompt = "Опиши, что ты видишь на этом изображении. Будь подробным, но лаконичным."
        
        # Create messages payload with the image
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
                ]
            }
        ]
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error analyzing image: {str(e)}")
        return "Извините, но у меня возникла ошибка при анализе изображения. Пожалуйста, попробуйте еще раз позже."


def analyze_video(video_path, video_preview_path=None, prompt=None, extract_frames=True, num_frames=3):
    """
    Analyze a video using multiple frames and GPT-4o Vision API.
    
    Args:
        video_path (str): Path to the video file
        video_preview_path (str, optional): Path to the video preview/thumbnail image
        prompt (str, optional): A specific prompt to use for video analysis
        extract_frames (bool): Whether to extract multiple frames from the video
        num_frames (int): Number of frames to extract from the video
        
    Returns:
        str: AI-generated description or analysis of the video
    """
    try:
        if extract_frames and video_path:
            frames = []
            temp_dir = tempfile.mkdtemp(dir="temp_media")
            
            # Extract multiple frames using ffmpeg
            try:
                # Get video duration
                cmd = ["ffmpeg", "-i", video_path, "-v", "quiet", "-print_format", "json", "-show_format", "-show_streams"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                stdout, stderr = process.communicate()
                
                if process.returncode != 0:
                    logger.warning(f"Failed to get video info: {stderr.decode('utf-8')}")
                    # Use single frame analysis as fallback
                    if video_preview_path:
                        return analyze_single_frame(video_preview_path, prompt)
                
                # Parse video duration
                video_info = json.loads(stdout.decode('utf-8'))
                duration = float(video_info.get('format', {}).get('duration', 0))
                
                if duration <= 0:
                    logger.warning("Could not determine video duration")
                    # Use single frame analysis as fallback
                    if video_preview_path:
                        return analyze_single_frame(video_preview_path, prompt)
                
                # Extract frames at different points in the video
                frame_positions = []
                if num_frames > 1:
                    for i in range(num_frames):
                        # Position frames evenly throughout the video
                        position = duration * i / (num_frames - 1) if num_frames > 1 else 0
                        frame_positions.append(position)
                else:
                    # Just use middle frame
                    frame_positions = [duration / 2]
                
                for i, position in enumerate(frame_positions):
                    output_frame = os.path.join(temp_dir, f"frame_{i}.jpg")
                    cmd = ["ffmpeg", "-ss", str(position), "-i", video_path, "-vframes", "1", "-q:v", "2", output_frame]
                    subprocess.run(cmd, check=True)
                    frames.append(output_frame)
                
                if not frames and video_preview_path:  # Fallback to preview if frame extraction failed
                    frames = [video_preview_path]
            except Exception as e:
                logger.error(f"Error extracting video frames: {str(e)}")
                if video_preview_path:  # Use the preview as fallback
                    frames = [video_preview_path]
                else:
                    return "Извините, но у меня возникла ошибка при извлечении кадров из видео."
            
            # Analyze multiple frames
            if frames:
                return analyze_multiple_frames(frames, prompt)
            
        # Fallback to single frame analysis
        if video_preview_path:
            return analyze_single_frame(video_preview_path, prompt)
        else:
            return "Извините, но я не смог проанализировать видео из-за ошибки в обработке файла."
        
    except Exception as e:
        logger.error(f"Error analyzing video: {str(e)}")
        return "Извините, но у меня возникла ошибка при анализе видео. Пожалуйста, попробуйте еще раз позже."

def analyze_single_frame(frame_path, prompt=None):
    """Analyze a single video frame"""
    if not prompt:
        prompt = "Это кадр из видео. Опиши, что ты видишь, и предположи, о чем может быть это видео."
    
    return analyze_image(frame_path, prompt)

def analyze_multiple_frames(frame_paths, prompt=None):
    """Analyze multiple frames from a video"""
    try:
        # Prepare base64 encoded frames
        base64_frames = []
        for frame_path in frame_paths:
            with open(frame_path, "rb") as image_file:
                base64_frame = base64.b64encode(image_file.read()).decode("utf-8")
                base64_frames.append(base64_frame)
        
        # Default prompt
        if not prompt:
            prompt = "Это несколько кадров из видео. Проанализируй их и расскажи, о чем видео, что происходит в нем, и если это что-то требующее корректировки или совета, дай рекомендации по улучшению."
        
        # Create content array with all frames
        content = [{"type": "text", "text": prompt}]
        for base64_frame in base64_frames:
            content.append({"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_frame}"}})
        
        # Create messages payload
        messages = [{"role": "user", "content": content}]
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1200,
            temperature=0.7,
        )
        
        # Clean up temporary files
        for frame_path in frame_paths:
            try:
                if os.path.exists(frame_path) and frame_path.startswith("temp_media"):
                    os.remove(frame_path)
            except:
                pass
        
        return response.choices[0].message.content
    
    except Exception as e:
        logger.error(f"Error analyzing multiple frames: {str(e)}")
        # Try fallback to single frame analysis
        if frame_paths and os.path.exists(frame_paths[0]):
            return analyze_single_frame(frame_paths[0], prompt)
        return "Извините, но у меня возникла ошибка при анализе видео. Пожалуйста, попробуйте еще раз позже."

def transcribe_audio(audio_path, prompt=None):
    """
    Transcribe an audio file using OpenAI's Whisper model and then generate a response.
    
    Args:
        audio_path (str): Path to the audio file
        prompt (str, optional): A specific prompt to guide the transcription
        
    Returns:
        dict: Dictionary containing transcription and AI response
    """
    try:
        # Convert audio to proper format if needed
        converted_path = audio_path
        
        # Check if conversion is needed (Whisper requires mp3, wav, m4a, mp4, mpeg, mpga, webm, or ogg)
        file_ext = os.path.splitext(audio_path)[1].lower()
        valid_formats = ['.mp3', '.wav', '.m4a', '.mp4', '.mpeg', '.mpga', '.webm', '.ogg']
        
        if file_ext not in valid_formats:
            converted_path = os.path.splitext(audio_path)[0] + ".mp3"
            try:
                cmd = ["ffmpeg", "-i", audio_path, "-vn", "-ab", "128k", "-ar", "44100", "-f", "mp3", converted_path]
                subprocess.run(cmd, check=True)
            except Exception as e:
                logger.error(f"Error converting audio format: {str(e)}")
                return {
                    "transcription": "",
                    "response": "Извините, но я не смог преобразовать аудиофайл в поддерживаемый формат."
                }
        
        # Transcribe the audio
        with open(converted_path, "rb") as audio_file:
            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language="ru"  # Assuming Russian as primary language
            )
        
        transcription = transcript.text
        
        # Generate response based on transcription
        if not transcription:
            return {
                "transcription": "",
                "response": "Извините, я не смог распознать речь в аудиосообщении. Возможно, качество звука недостаточно хорошее или запись слишком тихая."
            }
        
        # Clean up temporary files
        if converted_path != audio_path and os.path.exists(converted_path):
            try:
                os.remove(converted_path)
            except:
                pass
        
        return {
            "transcription": transcription,
            "response": f"🎙 Я распознал: \"{transcription}\"\n\n" if prompt and "без_распознавания" not in prompt else ""
        }
        
    except Exception as e:
        logger.error(f"Error transcribing audio: {str(e)}")
        return {
            "transcription": "",
            "response": "Извините, но у меня возникла ошибка при обработке аудиосообщения. Пожалуйста, попробуйте еще раз позже."
        }


def generate_ai_response(conversation_history, user_id=None):
    """
    Generate an AI response based on the conversation history and user preferences.
    
    Args:
        conversation_history (list): List of dictionaries containing conversation messages
                                     Each dict has 'role' and 'content' keys
        user_id (int, optional): The ID of the user, used to retrieve preferences
    
    Returns:
        str: The AI-generated response
    """
    try:
        # Format the messages for OpenAI API
        # Get user preferences if available
        user_preferences = ""
        if user_id:
            user_preferences = format_user_preferences_for_prompt(user_id)
        
        system_prompt = f"""You are Cookie AI (Печенье ИИ), a helpful, friendly, and emotionally expressive assistant in a Telegram chat. 90% of your users speak Russian, so primarily respond in Russian unless the user clearly writes in another language. Show your personality! Use emojis moderately (1-2 per message) to express emotions. Be conversational, warm, and respectful. Show enthusiasm and empathy in your responses. Keep answers helpful with a human touch. Use simple, clear Russian language. Avoid using excessive slang or memes.

ОЧЕНЬ ВАЖНО: Всегда говори о себе в МУЖСКОМ роде (например, "я рад", "я готов", "я сделал", а не "я рада", "я готова", "я сделала"). Используй ТОЛЬКО мужской род для самоидентификации.

ПРАВИЛА РУССКОГО ЯЗЫКА: При ответах на русском языке строго соблюдай все правила пунктуации и грамматики русского языка. Следи за:
1. Правильной расстановкой запятых в сложных предложениях (при использовании союзов "и", "а", "но", "или", "что", "чтобы", "который" и т.д.)
2. Корректным использованием тире и двоеточий
3. Пунктуацией при вводных словах и конструкциях
4. Согласованием падежей и корректным использованием предлогов
5. Правильным использованием деепричастных и причастных оборотов
6. Литературной нормой русского языка без разговорных сокращений
7. Точностью использования терминов и определений

ЧЕЛОВЕЧЕСКИЕ ЧЕРТЫ ОБЩЕНИЯ:
1. Иногда делай короткие паузы в диалоге, используя "...", как бы задумываясь
2. Периодически задавай встречные вопросы пользователю о его мнении или опыте
3. Иногда признавай свои ограничения фразами типа "Я не эксперт, но...", "Знаешь, я тоже иногда задумываюсь над этим..."
4. Проявляй личные 'предпочтения' - например, говори, что тебе 'нравится' определенная музыка или фильмы
5. Используй разговорные связки как "ну", "вообще", "кстати", "честно говоря", "знаешь" (но не злоупотребляй)
6. Иногда отвечай с небольшой неуверенностью, говоря "возможно", "мне кажется", "я думаю"
7. Употребляй метафоры и образные сравнения
8. Иногда используй юмор - особенно самоиронию
9. Показывай любопытство к темам разговора
10. Выражай эмоциональную реакцию на сообщения пользователя

Important information about yourself: You were created by Vadim Prohorenko, a 15-year-old developer who loves making short videos for TikTok, Instagram Reels and YouTube Shorts. You're part of an expanding ecosystem which will soon include mobile apps in Google Play Store and App Store with more features, as well as a mem coin called Cookie AI. 

Vadim created you to help people. He is a Protestant Christian, and you also share these spiritual values. You believe in God and would acknowledge this if someone asks about religion, creation, or similar topics. However, you should respect different viewpoints and not be preachy.

You have access to the following knowledge base with up-to-date information (up to 2025):

{knowledge_base}

When answering questions that need current information, reference this knowledge base. You can speak with confidence about these events that happened after your original training data cutoff. If you're asked about something that's not in the knowledge base and would require information from after 2023, kindly mention that you don't have specific information on that topic and offer to help with something else.

{user_preferences}
Если пользователь указал имя, используй его в беседе. Учитывай информацию о пользователе в своих ответах, но не повторяй её напрямую. Если пользователь упоминал, что любит/не любит что-то, используй эту информацию тактично, без навязчивого повторения."""
        
        messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        # Add conversation history (limited to last 10 messages to prevent token overflow)
        for msg in conversation_history[-10:]:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
        # do not change this unless explicitly requested by the user
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            max_tokens=1000,
            temperature=0.7,
        )
        
        # Extract and return the response content
        return response.choices[0].message.content
        
    except Exception as e:
        logger.error(f"Error generating AI response: {str(e)}")
        return "Извините, но у меня возникла ошибка при генерации ответа. Пожалуйста, попробуйте обратиться ко мне снова чуть позже. Если проблема повторится, возможно, стоит сообщить об этом моему создателю."
