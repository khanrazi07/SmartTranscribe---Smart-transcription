from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from youtube_transcript_api import YouTubeTranscriptApi
import yt_dlp
import speech_recognition as sr
import os
import tempfile
from urllib.parse import urlparse, parse_qs

app = FastAPI(title="SAM - Video Transcription API", version="1.0.0")

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
    Supports: youtube.com/watch?v=ID, youtu.be/ID
    """
    try:
        if 'youtu.be' in url:
            return url.split('/')[-1].split('?')[0]
        
        if 'youtube.com' in url:
            parsed = parse_qs(urlparse(url).query)
            video_id = parsed.get('v', [None])[0]
            if video_id:
                return video_id
        
        # If it's just an ID
        if len(url) == 11:
            return url
            
        raise ValueError("Invalid YouTube URL")
    except Exception as e:
        raise Exception(f"Failed to extract video ID: {str(e)}")

def get_youtube_transcript(video_url: str) -> str:
    """
    Get transcript from YouTube video using YouTube Transcript API
    """
    try:
        video_id = extract_youtube_video_id(video_url)
        print(f"Getting transcript for YouTube video ID: {video_id}")
        
        # Get transcript - this is the correct method
        transcript_list = YouTubeTranscriptApi.get_transcripts([video_id])
        
        # Get the first available transcript
        if video_id in transcript_list:
            transcript_items = transcript_list[video_id]
        else:
            raise Exception("No transcripts found for this video")
        
        # Combine all transcript text
        transcript = " ".join([item['text'] for item in transcript_items])
        print(f"Got transcript with {len(transcript)} characters")
        
        return transcript
        
    except Exception as e:
        raise Exception(f"Failed to get YouTube transcript: {str(e)}")

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
    
    Strategy:
    - YouTube: Uses YouTube Transcript API (fast, free, accurate)
    - Other platforms: Downloads audio + transcribes with SpeechRecognition
    
    Supports:
    - YouTube (via Transcript API)
    - Vimeo, TikTok, Instagram, Twitter, Rumble, DailyMotion (via yt-dlp + SpeechRecognition)
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
        
        # Step 1: Get transcript based on platform
        if platform == 'youtube':
            print("Using YouTube Transcript API...")
            transcript = get_youtube_transcript(video_data.url)
        else:
            print(f"Using yt-dlp + SpeechRecognition for {platform}...")
            
            # Create temporary directory for audio processing
            temp_dir = tempfile.mkdtemp()
            output_template = os.path.join(temp_dir, "audio")
            
            # Extract audio
            audio_file = extract_audio_via_ytdlp(video_data.url, output_template)
            
            # Transcribe audio
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
        "strategy": {
            "youtube": "YouTube Transcript API (fast, free, accurate)",
            "other_platforms": "yt-dlp + SpeechRecognition",
            "supported_platforms": [
                "YouTube",
                "Vimeo",
                "TikTok",
                "Instagram",
                "Twitter/X",
                "Rumble",
                "DailyMotion",
                "And 1000+ more"
            ]
        }
    }

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
