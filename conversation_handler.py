import logging

# Set up logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# In-memory storage for conversations
# Structure: {user_id: [{"role": "user/assistant", "content": "message"}, ...]}
conversation_store = {}

def get_conversation_history(user_id):
    """
    Retrieve conversation history for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        list: List of conversation messages
    """
    if user_id not in conversation_store:
        conversation_store[user_id] = []
    
    return conversation_store[user_id]

def add_to_conversation(user_id, role, content):
    """
    Add a message to the conversation history.
    
    Args:
        user_id: The user's unique identifier
        role (str): Either 'user' or 'assistant'
        content (str): The message content
        
    Returns:
        None
    """
    if user_id not in conversation_store:
        conversation_store[user_id] = []
    
    # Ensure the role is valid
    if role not in ["user", "assistant", "system"]:
        logger.warning(f"Invalid role '{role}' provided. Must be 'user', 'assistant', or 'system'.")
        return
    
    # Add the message to the conversation history
    conversation_store[user_id].append({
        "role": role,
        "content": content
    })
    
    # Limit conversation history to last 50 messages to prevent memory issues
    if len(conversation_store[user_id]) > 50:
        conversation_store[user_id] = conversation_store[user_id][-50:]

def clear_conversation(user_id):
    """
    Clear the conversation history for a specific user.
    
    Args:
        user_id: The user's unique identifier
        
    Returns:
        None
    """
    conversation_store[user_id] = []
