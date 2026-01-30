from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import yt_dlp
import whisper
import os
import tempfile
from pathlib import Path

app = FastAPI(title="Video Transcription API", version="1.0.0")

# Load Whisper model once at startup
print("Loading Whisper base model... this may take a moment on first run")
whisper_model = whisper.load_model("tiny")

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
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'outtmpl': output_path,
            'quiet': False,
            'no_warnings': False,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            print(f"Downloading audio from: {video_url}")
            info = ydl.extract_info(video_url, download=True)
            audio_file = ydl.prepare_filename(info)
            # Convert to mp3 path
            audio_file = os.path.splitext(audio_file)[0] + '.mp3'
            return audio_file
            
    except Exception as e:
        raise Exception(f"Failed to extract audio: {str(e)}")

def transcribe_audio(audio_path: str) -> str:
    """
    Transcribe audio file using Whisper
    Returns the transcript text
    """
    try:
        print(f"Transcribing audio: {audio_path}")
        result = whisper_model.transcribe(audio_path)
        transcript = result['text']
        return transcript
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
    uvicorn.run(app, host="127.0.0.1", port=8007)
