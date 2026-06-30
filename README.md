# Chat AI - OpenRouter Chat App

A Streamlit-based chat application with OpenRouter API integration for using DeepSeek, GPT-4, Claude, and other models.

## Features

- 🤖 **Model Selection**: Browse available models, auto-select or manually choose
- 💬 **Chat Interface**: Simple ChatGPT-like interface
- 💾 **Session Management**: Save, load, rename, and search chat sessions
- 🔍 **Search History**: Search through past conversations
- 💰 **Pricing Info**: View model pricing (input/output tokens)
- 🌐 **OpenRouter Integration**: Use any model available on OpenRouter

## Setup

1. Clone the repo
2. Install dependencies: `pip install -r requirements.txt`
3. Get OpenRouter API key from https://openrouter.ai
4. Run: `streamlit run app.py`
5. Enter your API key in the sidebar

## Deployment on Streamlit Cloud

1. Push to GitHub
2. Go to https://streamlit.io/cloud
3. Connect your repo
4. Add `OPENROUTER_API_KEY` to Streamlit Cloud secrets (optional)

## Tech Stack

- Streamlit
- OpenRouter API
- Python requests
- JSON for session storage
