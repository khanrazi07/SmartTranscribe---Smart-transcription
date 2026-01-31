from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests
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

def extract_youtube_video_id(url: str) -> str:
    """
    Extract video ID from YouTube URL
    Supports formats: youtube.com/watch?v=ID, youtu.be/ID
    """
    try:
        # Handle youtu.be format
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
        
        # Handle youtube.com format
        if 'youtube.com' in url:
            parsed = parse_qs(urlparse(url).query)
            return parsed.get('v', [None])[0]
        
        # If it's just an ID
        if len(url) == 11:
            return url
            
        raise ValueError("Invalid YouTube URL")
    except Exception as e:
        raise Exception(f"Failed to extract video ID: {str(e)}")

def get_youtube_audio_url(video_url: str) -> str:
    """
    Get MP3 download URL from RapidAPI YouTube downloader
    """
    try:
        video_id = extract_youtube_video_id(video_url)
        
        print(f"Getting MP3 URL for video ID: {video_id}")
        
        url = "https://youtube-mp3-audio-video-downloader.p.rapidapi.com/dl"
        
        querystring = {"id": video_id}
        
        headers = {
            "x-rapidapi-key": RAPIDAPI_KEY,
            "x-rapidapi-host": RAPIDAPI_HOST
        }
        
        response = requests.get(url, headers=headers, params=querystring, timeout=30)
        
        if response.status_code != 200:
            raise Exception(f"RapidAPI error: {response.text}")
        
        data = response.json()
        
        if 'link' not in data:
            raise Exception("Could not get download link from API")
        
        mp3_url = data['link']
        print(f"Got MP3 URL: {mp3_url}")
        
        return mp3_url
        
    except Exception as e:
        raise Exception(f"Failed to get YouTube audio: {str(e)}")

def download_audio_from_url(audio_url: str, output_path: str) -> str:
    """
    Download MP3 audio from URL
    """
    try:
        print(f"Downloading audio from: {audio_url}")
        
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

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using SpeechRecognition
    Returns the transcript text
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
    Endpoint to transcribe a video from URL
    Supports: YouTube, and any platform supported by RapidAPI
    
    Args:
        video_data: Object containing video URL
        
    Returns:
        TranscriptionResponse with URL and full transcript
    """
    temp_dir = None
    try:
        # Create temporary directory for audio processing
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, "audio")
        
        # Step 1: Get MP3 URL from RapidAPI
        audio_url = get_youtube_audio_url(video_data.url)
        
        # Step 2: Download audio
        audio_file = download_audio_from_url(audio_url, output_template)
        
        # Step 3: Transcribe audio
        transcript = transcribe_audio(audio_file)
        
        # Return response
        return TranscriptionResponse(
            url=video_data.url,
            transcript=transcript,
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
    return {"status": "healthy", "service": "SAM - Video Transcription API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
