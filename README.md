# Telegram AI Assistant Bot

This is a Telegram bot that uses OpenAI's GPT-4o model to generate intelligent responses to user messages. The bot remembers conversation history and provides helpful AI-powered responses.

## Features

- Responds to basic commands (/start, /help, /clear)
- Integrates with OpenAI API for generating AI responses
- Maintains conversation history for context
- Provides inline buttons for easy command selection
- Handles errors gracefully
- Flask keep-alive server ensures 24/7 operation
- Threaded architecture for better performance and reliability

## Prerequisites

- Python 3.9+
- Telegram Bot Token (get from [@BotFather](https://t.me/BotFather))
- OpenAI API Key (get from [OpenAI Dashboard](https://platform.openai.com/api-keys))
- Heroku account (for deployment)

## Local Installation

1. Clone the repository
2. Install dependencies:
   ```bash
   pip install pyTelegramBotAPI openai python-dotenv flask
   ```
3. Create a `.env` file in the root directory with the following content:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token_here
   OPENAI_API_KEY=your_openai_api_key_here
   ```
4. Run the bot:
   ```bash
   python bot.py
   ```

## Railway Deployment

To run the bot 24/7, you can deploy it to Railway:

1. Sign up for a Railway account at https://railway.app/ (you can use your GitHub account to sign up)

2. Install the Railway CLI (optional, but useful):
   ```bash
   # Install using npm
   npm i -g @railway/cli
   
   # Log in to Railway
   railway login
   ```

3. Fork or push this repository to your GitHub account 
   (or you can deploy directly from your local machine using the Railway CLI)

4. Create a new project in Railway:
   - Click "New Project" in the Railway dashboard
   - Select "Deploy from GitHub repo" 
   - Select your repository
   - Or use CLI: `railway init`

5. Rename `railway-requirements.txt` to `requirements.txt` before deploying:
   ```bash
   mv railway-requirements.txt requirements.txt
   ```

6. Set up environment variables in Railway:
   - Go to your project in the Railway dashboard
   - Click on "Variables" tab
   - Add the following variables:
     - `TELEGRAM_TOKEN=your_telegram_bot_token_here`
     - `OPENAI_API_KEY=your_openai_api_key_here`
     - `PORT=8080` (for the keep-alive server)
   - Or use CLI: `railway variables set TELEGRAM_TOKEN=your_token OPENAI_API_KEY=your_key PORT=8080`

7. Configure the service:
   - In the "Settings" tab, set the following:
   - For "Start Command", enter: `python bot.py`
   
   **Alternative: Docker Deployment**
   - Railway also supports Docker deployments
   - This repository includes a `Dockerfile` for easy deployment
   - Railway will automatically detect and use the Dockerfile

8. Deploy your project:
   - Railway will automatically deploy your app when you push to GitHub
   - Or use CLI: `railway up`

9. Monitor your deployment:
   - Click on the "Deployments" tab to see deployment status
   - Check logs by clicking on the "Logs" button
   - Or use CLI: `railway logs`

Your bot should now be running 24/7 on Railway servers! Railway will automatically restart your bot if it crashes and provides automatic HTTPS and other modern deployment features.

## Keep-Alive Functionality

This bot includes a Flask-based keep-alive server that runs in a separate thread. This provides several benefits:

1. **Prevents Idle Timeouts**: Some hosting platforms shut down apps that don't receive HTTP traffic. The Flask server keeps the app active by accepting HTTP requests.

2. **Health Checks**: The `/health` endpoint allows monitoring services to verify the bot is running properly.

3. **Status Page**: Visiting the root URL shows a simple status page confirming the bot is operational.

The keep-alive server doesn't interfere with the bot's main functionality and uses minimal resources. It runs on port 8080 and is automatically started when you run the bot.

## Replit Deployment

You can also deploy this bot on Replit for 24/7 operation:

1. Create a new Replit project or fork this repository to Replit

2. Set up environment secrets in Replit:
   - Click on "Secrets" (lock icon) in the sidebar
   - Add the following secrets:
     - `TELEGRAM_TOKEN` = your_telegram_bot_token
     - `OPENAI_API_KEY` = your_openai_api_key

3. Install dependencies:
   - Replit will automatically detect and install dependencies from `pyproject.toml`
   - Alternatively, you can use the Shell to run: `pip install pyTelegramBotAPI openai python-dotenv flask`

4. Run the bot:
   - Click the "Run" button at the top
   - The bot will start and the keep-alive server will prevent Replit from timing out

5. Configure as Always On (optional):
   - If you have Replit Pro, enable "Always On" in the project settings to ensure the bot runs continuously without needing pings from external services

The bot is now deployed on Replit and will remain active thanks to the keep-alive server.