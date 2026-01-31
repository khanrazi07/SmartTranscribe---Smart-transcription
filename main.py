from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import speech_recognition as sr
import os
import tempfile
from pathlib import Path

app = FastAPI(title="Video Transcription API", version="1.0.0")

class VideoURL(BaseModel):
    url: str

class TranscriptionResponse(BaseModel):
    url: str
    transcript: str
    status: str

def extract_audio_from_video(video_url: str, output_path: str) -> str:
    """
    Extract audio from video URL using yt-dlp
    Returns path to the audio file
    """
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'wav',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
            'socket_timeout': 30,
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'extractor_args': {
                'youtube': {
                    'skip': ['webpage']
                }
            }
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading audio from: {video_url}")
            info = ydl.extract_info(video_url, download=True)
            audio_file = ydl.prepare_filename(info)
            # Convert to wav path
            audio_file = os.path.splitext(audio_file)[0] + '.wav'
            return audio_file
            
    except Exception as e:
        raise Exception(f"Failed to extract audio: {str(e)}")

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
        
        # Step 1: Extract audio from video
        audio_file = extract_audio_from_video(video_data.url, output_template)
        
        # Step 2: Transcribe audio
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
    return {"status": "healthy", "service": "Video Transcription API"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
