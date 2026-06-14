# Intelligent Maintenance Wizard — Setup Guide

## Prerequisites
- Python 3.9+ installed
- Google Gemini API key (free at https://aistudio.google.com/apikey)

## Quick Start

### 1. Install Dependencies
```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure API Key
```bash
# Copy the example env file
copy .env.example .env

# Edit .env and add your API key of choice
# NVIDIA_API_KEY=your_nvidia_key_here
# GROQ_API_KEY=your_groq_key_here
# OPENROUTER_API_KEY=your_openrouter_key_here
# GOOGLE_API_KEY=your_google_key_here
```

### 3. Run the Server
```bash
cd backend
python main.py
```

### 4. Open the Dashboard
Navigate to **http://localhost:8000** in your browser.

## What Happens on First Run
1. SQLite database is created and seeded with 10 steel plant equipment units
2. Historical sensor data (7 days) is generated
3. Knowledge base documents are indexed into ChromaDB vector store
4. Sensor simulator starts generating real-time data every 5 seconds
5. Frontend dashboard is served at the root URL

## Environment Variables
| Variable | Default | Description |
|----------|---------|-------------|
| NVIDIA_API_KEY | - | NVIDIA API key for ultra-fast reasoning |
| GROQ_API_KEY | - | Groq Cloud API key |
| OPENROUTER_API_KEY | - | OpenRouter API key |
| GOOGLE_API_KEY | - | Google Gemini API key |
| LLM_MODEL | meta/llama-3.1-70b-instruct | Primary LLM model to use |
| PORT | 8000 | Server port |
| SENSOR_INTERVAL | 5 | Sensor reading interval in seconds |
| ANOMALY_PROBABILITY | 0.05 | Probability of anomaly in sensor readings |
| RAG_TOP_K | 5 | Number of RAG results to retrieve |

## Troubleshooting
- **No AI responses**: Ensure at least one of the API keys (NVIDIA, Groq, OpenRouter, Google) is configured in your .env file
- **ChromaDB errors**: Delete the `chroma_db/` folder and restart the server
- **Database errors**: Delete `maintenance_wizard.db` and restart the server
- **Port in use**: Change PORT in your .env file
