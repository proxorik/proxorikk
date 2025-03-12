from flask import Flask
from threading import Thread
import logging

# Disable Flask's default logging to avoid cluttering the console
logging.getLogger('werkzeug').setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def home():
    """
    Home page for the keep-alive server.
    Returns a simple message to indicate the bot is running.
    """
    return "Your Telegram bot is alive and running!"

@app.route('/health')
def health():
    """
    Health check endpoint for monitoring services.
    """
    return "OK", 200

def run():
    """
    Run the Flask server on port 8080 with host 0.0.0.0 
    to make it accessible from outside the container.
    """
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    """
    Start the keep-alive server in a separate thread.
    """
    t = Thread(target=run)
    t.daemon = True  # Make the thread a daemon so it terminates when the main program ends
    t.start()
    return t