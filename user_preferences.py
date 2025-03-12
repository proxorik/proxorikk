#!/usr/bin/env python
# -*- coding: utf-8 -*-

import json
import os
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Path to store user preferences
PREFERENCES_FOLDER = "user_data"
PREFERENCES_FILE = os.path.join(PREFERENCES_FOLDER, "user_preferences.json")

# Ensure the user data folder exists
os.makedirs(PREFERENCES_FOLDER, exist_ok=True)

# Initialize the preferences storage
preferences = {}

# Try to load existing preferences
def load_preferences():
    """Load user preferences from file."""
    global preferences
    try:
        if os.path.exists(PREFERENCES_FILE):
            with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                preferences = json.load(f)
    except Exception as e:
        logger.error(f"Error loading user preferences: {e}")
        preferences = {}

# Save preferences to file
def save_preferences():
    """Save user preferences to file."""
    try:
        with open(PREFERENCES_FILE, 'w', encoding='utf-8') as f:
            json.dump(preferences, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"Error saving user preferences: {e}")

# Extract and store user preferences from conversation
def update_user_preferences(user_id, message_text):
    """
    Analyze user message and update preferences if personal information is detected.
    
    Args:
        user_id: The unique ID of the user
        message_text: The text message from the user
    """
    user_id = str(user_id)  # Ensure user_id is string
    
    # Initialize user preferences if not exist
    if user_id not in preferences:
        preferences[user_id] = {
            "first_interaction": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "topics": {},
            "personal_info": {}
        }
    
    # Update last interaction time
    preferences[user_id]["last_interaction"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Update interaction count
    preferences[user_id]["interaction_count"] = preferences[user_id].get("interaction_count", 0) + 1
    
    # Look for potential personal information to store
    # This is a simple approach - more sophisticated extraction would require NLP
    
    # Check for name mentions
    if "меня зовут" in message_text.lower() or "я" in message_text.lower() and "зовусь" in message_text.lower():
        words = message_text.split()
        name_idx = -1
        
        for i, word in enumerate(words):
            if word.lower() == "зовут" or word.lower() == "зовусь":
                name_idx = i + 1
                break
        
        if name_idx >= 0 and name_idx < len(words):
            name = words[name_idx].strip(".,!?")
            if len(name) > 1 and name[0].isupper():  # Basic check for name validity
                preferences[user_id]["personal_info"]["name"] = name
    
    # Check for age mentions
    if "мне" in message_text.lower() and "лет" in message_text.lower():
        words = message_text.split()
        for i, word in enumerate(words):
            if word.lower() == "мне" and i+1 < len(words):
                potential_age = words[i+1].strip(".,!?")
                if potential_age.isdigit() and 1 <= int(potential_age) <= 120:
                    preferences[user_id]["personal_info"]["age"] = int(potential_age)
    
    # Check for hobby mentions
    hobby_triggers = ["увлекаюсь", "люблю", "моё хобби", "мое хобби", "занимаюсь"]
    for trigger in hobby_triggers:
        if trigger in message_text.lower():
            # Just store the full message for now, 
            # could be enhanced with more sophisticated extraction
            if "hobbies" not in preferences[user_id]["personal_info"]:
                preferences[user_id]["personal_info"]["hobbies"] = []
            preferences[user_id]["personal_info"]["hobbies"].append(message_text)
            break
    
    # Check for preferences/likes
    like_triggers = ["люблю", "нравится", "обожаю", "предпочитаю"]
    for trigger in like_triggers:
        if trigger in message_text.lower():
            if "likes" not in preferences[user_id]["personal_info"]:
                preferences[user_id]["personal_info"]["likes"] = []
            preferences[user_id]["personal_info"]["likes"].append(message_text)
            break
    
    # Check for dislikes
    dislike_triggers = ["не люблю", "ненавижу", "не нравится"]
    for trigger in dislike_triggers:
        if trigger in message_text.lower():
            if "dislikes" not in preferences[user_id]["personal_info"]:
                preferences[user_id]["personal_info"]["dislikes"] = []
            preferences[user_id]["personal_info"]["dislikes"].append(message_text)
            break
    
    # Store message to topic analysis
    # Here we simply tokenize and count words
    topic_words = [word.strip(".,!?()[]{}:;\"'").lower() for word in message_text.split() if len(word) > 3]
    for word in topic_words:
        if word not in preferences[user_id]["topics"]:
            preferences[user_id]["topics"][word] = 0
        preferences[user_id]["topics"][word] += 1
    
    # Save preferences
    save_preferences()

def get_user_preferences(user_id):
    """
    Get stored preferences for a user.
    
    Args:
        user_id: The unique ID of the user
        
    Returns:
        dict: User's preferences or empty dict if not found
    """
    user_id = str(user_id)
    if user_id in preferences:
        return preferences[user_id]
    return {}

def format_user_preferences_for_prompt(user_id):
    """
    Format the user preferences into a string that can be added to the AI prompt.
    
    Args:
        user_id: The unique ID of the user
        
    Returns:
        str: Formatted user preferences
    """
    user_id = str(user_id)
    if user_id not in preferences:
        return ""
    
    user_pref = preferences[user_id]
    result = "Информация о пользователе:\n"
    
    # Add personal info
    if "personal_info" in user_pref and user_pref["personal_info"]:
        if "name" in user_pref["personal_info"]:
            result += f"- Имя пользователя: {user_pref['personal_info']['name']}\n"
        
        if "age" in user_pref["personal_info"]:
            result += f"- Возраст: {user_pref['personal_info']['age']}\n"
        
        if "hobbies" in user_pref["personal_info"] and user_pref["personal_info"]["hobbies"]:
            result += "- Пользователь упоминал интересы и хобби:\n"
            for hobby in user_pref["personal_info"]["hobbies"][-3:]:  # Last 3 mentions
                result += f"  * {hobby}\n"
        
        if "likes" in user_pref["personal_info"] and user_pref["personal_info"]["likes"]:
            result += "- Пользователь упоминал, что ему нравится:\n"
            for like in user_pref["personal_info"]["likes"][-3:]:  # Last 3 mentions
                result += f"  * {like}\n"
        
        if "dislikes" in user_pref["personal_info"] and user_pref["personal_info"]["dislikes"]:
            result += "- Пользователь упоминал, что ему не нравится:\n"
            for dislike in user_pref["personal_info"]["dislikes"][-3:]:  # Last 3 mentions
                result += f"  * {dislike}\n"
    
    # Add interaction history
    result += f"- Количество взаимодействий с ботом: {user_pref.get('interaction_count', 0)}\n"
    
    # Add top topics of interest
    if "topics" in user_pref and user_pref["topics"]:
        topics = sorted(user_pref["topics"].items(), key=lambda x: x[1], reverse=True)[:5]
        if topics:
            result += "- Частые темы в разговорах:\n"
            for topic, count in topics:
                result += f"  * {topic}\n"
    
    return result

# Load preferences on module import
load_preferences()