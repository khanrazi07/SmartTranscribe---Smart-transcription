# Video Transcription API - Setup & Usage Guide

## Prerequisites
- Python 3.8+
- FFmpeg (required by yt-dlp for audio conversion)
- pip (Python package manager)

## Installation

### Step 1: Install FFmpeg
**On Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install ffmpeg
```

**On macOS (with Homebrew):**
```bash
brew install ffmpeg
```

**On Windows:**
Download from https://ffmpeg.org/download.html or use:
```bash
choco install ffmpeg
```

### Step 2: Set up Python Environment
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate
```

### Step 3: Install Dependencies
```bash
pip install -r requirements.txt
```

## Running the API

```bash
python main.py
```

The API will start at `http://localhost:8000`

## API Documentation

Once running, visit:
- **Interactive Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Endpoints

### 1. Transcribe Video
**Endpoint:** `POST /transcribe`

**Request Body:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
}
```

**Response:**
```json
{
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "transcript": "Full transcribed text from the video...",
  "status": "success"
}
```

### 2. Health Check
**Endpoint:** `GET /health`

**Response:**
```json
{
  "status": "healthy",
  "service": "Video Transcription API"
}
```

## Testing with curl

```bash
# Test health check
curl http://localhost:8000/health

# Transcribe a video
curl -X POST http://localhost:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}'
```

## Testing with Python requests

```python
import requests

url = "http://localhost:8000/transcribe"
data = {"url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ"}

response = requests.post(url, json=data)
print(response.json())
```

## Performance Notes

- **First Run**: The Whisper base model (~140MB) will be downloaded automatically on first run
- **Transcription Time**: Depends on video length, typically 1-2 minutes per 30 minutes of video
- **Supported Platforms**: YouTube, Vimeo, TikTok, Instagram, and 1000+ other platforms (yt-dlp supported)

## Troubleshooting

**Error: "FFmpeg not found"**
- Make sure FFmpeg is installed and in your PATH

**Error: "Video download failed"**
- Check if the URL is publicly accessible
- Some platforms may have regional restrictions

**Slow transcription**
- This is normal for the base model. If you need faster processing, use the "tiny" model instead
- Edit `main.py` line 13: `whisper_model = whisper.load_model("tiny")`

## Next Steps

Once you've verified the transcription works, you can add:
1. Text chunking
2. Embedding generation
3. Pinecone vector storage
4. RAG setup
5. LLM integration
