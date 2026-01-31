from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
import yt_dlp
import speech_recognition as sr
import os
import tempfile
from pathlib import Path
from urllib.parse import urlparse, parse_qs

app = FastAPI(title="SAM - Video Transcription API", version="1.0.0")

# RapidAPI Configuration
RAPIDAPI_KEY = os.environ.get("RAPIDAPI_KEY", "9b02f05b1fmshc08b204919e8897p16a9dbjsn8c5cd99c6d36")
RAPIDAPI_HOST = "youtube-mp3-audio-video-downloader.p.rapidapi.com"

class VideoURL(BaseModel):
    url: str

class TranscriptionResponse(BaseModel):
    url: str
    transcript: str
    status: str
    platform: str

def detect_platform(url: str) -> str:
    """
    Detect which video platform the URL belongs to
    """
    url_lower = url.lower()
    
    if 'youtube.com' in url_lower or 'youtu.be' in url_lower:
        return 'youtube'
    elif 'vimeo.com' in url_lower:
        return 'vimeo'
    elif 'tiktok.com' in url_lower:
        return 'tiktok'
    elif 'instagram.com' in url_lower:
        return 'instagram'
    elif 'twitter.com' in url_lower or 'x.com' in url_lower:
        return 'twitter'
    elif 'rumble.com' in url_lower:
        return 'rumble'
    elif 'dailymotion.com' in url_lower:
        return 'dailymotion'
    else:
        return 'other'

def extract_youtube_video_id(url: str) -> str:
    """
    Extract video ID from YouTube URL
    """
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
        
        if 'youtube.com' in url:
            parsed = parse_qs(urlparse(url).query)
            return parsed.get('v', [None])[0]
        
        if len(url) == 11:
            return url
            
        raise ValueError("Invalid YouTube URL")
    except Exception as e:
        raise Exception(f"Failed to extract video ID: {str(e)}")

def get_youtube_audio_via_rapidapi(video_url: str) -> str:
    """
    Get MP3 download URL from RapidAPI for YouTube videos
    """
    try:
        video_id = extract_youtube_video_id(video_url)
        
        print(f"Getting MP3 URL for YouTube video ID: {video_id}")
        
        url = "https://youtube-mp3-audio-video-downloader.p.rapidapi.com/get-download-link"
        
        querystring = {"video_id": video_id, "format": "mp3"}
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"RapidAPI error: {response.text}")
        
        data = response.json()
        
        # The response might have different key names, try common ones
        mp3_url = data.get('link') or data.get('url') or data.get('download_url') or data.get('mp3_url')
        
        if not mp3_url:
            raise Exception(f"Could not find MP3 URL in response: {data}")
        
        print(f"Got MP3 URL: {mp3_url}")
        
        return mp3_url
        
    except Exception as e:
        raise Exception(f"Failed to get YouTube audio via RapidAPI: {str(e)}")

def download_audio_from_url(audio_url: str, output_path: str) -> str:
    """
    Download audio file from direct URL
    """
    try:
        print(f"Downloading audio from URL: {audio_url}")
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(audio_url, headers=headers, timeout=60)
        
        if response.status_code != 200:
            raise Exception(f"Download failed with status {response.status_code}")
        
        # Save to file
        output_file = output_path + ".mp3"
        with open(output_file, 'wb') as f:
            f.write(response.content)
        
        print(f"Audio saved to: {output_file}")
        return output_file
        
    except Exception as e:
        raise Exception(f"Failed to download audio: {str(e)}")

def extract_audio_via_ytdlp(video_url: str, output_path: str) -> str:
    """
    Extract audio from video using yt-dlp (for non-YouTube platforms)
    """
    try:
        print(f"Extracting audio using yt-dlp from: {video_url}")
        
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            audio_file = ydl.prepare_filename(info)
            audio_file = os.path.splitext(audio_file)[0] + '.mp3'
            print(f"Audio extracted to: {audio_file}")
            return audio_file
            
    except Exception as e:
        raise Exception(f"Failed to extract audio via yt-dlp: {str(e)}")

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using SpeechRecognition with Google API
    """
    try:
        print(f"Transcribing audio: {audio_path}")
        recognizer = sr.Recognizer()
        
        with sr.AudioFile(audio_path) as source:
            audio = recognizer.record(source)
        
        # Try Google Speech Recognition (free, no API key needed)
        try:
            transcript = recognizer.recognize_google(audio)
            return transcript
        except sr.UnknownValueError:
            return "Could not understand the audio"
        except sr.RequestError as e:
            raise Exception(f"Speech recognition service error: {str(e)}")
            
    except Exception as e:
        raise Exception(f"Failed to transcribe audio: {str(e)}")

@app.post("/transcribe", response_model=TranscriptionResponse)
async def transcribe_video(video_data: VideoURL):
    """
    Endpoint to transcribe any video from URL
    
    Supports:
    - YouTube (via RapidAPI)
    - Vimeo, TikTok, Instagram, Twitter, Rumble, DailyMotion (via yt-dlp)
    - And 1000+ other platforms via yt-dlp
    
    Args:
        video_data: Object containing video URL
        
    Returns:
        TranscriptionResponse with URL, transcript, platform, and status
    """
    temp_dir = None
    try:
        # Detect platform
        platform = detect_platform(video_data.url)
        print(f"Detected platform: {platform}")
        
        # Create temporary directory for audio processing
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, "audio")
        
        # Step 1: Get audio based on platform
        if platform == 'youtube':
            print("Using RapidAPI for YouTube...")
            audio_url = get_youtube_audio_via_rapidapi(video_data.url)
            audio_file = download_audio_from_url(audio_url, output_template)
        else:
            print(f"Using yt-dlp for {platform}...")
            audio_file = extract_audio_via_ytdlp(video_data.url, output_template)
        
        # Step 2: Transcribe audio
        transcript = transcribe_audio(audio_file)
        
        # Return response
        return TranscriptionResponse(
            url=video_data.url,
            transcript=transcript,
            platform=platform,
            status="success"
        )
        
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
    finally:
        # Cleanup temporary files
        if temp_dir and os.path.exists(temp_dir):
            import shutil
            shutil.rmtree(temp_dir)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "SAM - Video Transcription API",
        "supported_platforms": [
            "YouTube (via RapidAPI)",
            "Vimeo",
            "TikTok",
            "Instagram",
            "Twitter/X",
            "Rumble",
            "DailyMotion",
            "And 1000+ more via yt-dlp"
        ]
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
