import requests
import json
import sys

# Configuration
API_BASE_URL = "http://localhost:8003"

def test_health():
    """Test the health endpoint"""
    print("\n=== Testing Health Endpoint ===")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API. Make sure it's running on port 8003")
        return False

def transcribe_video(video_url):
    """Transcribe a video from URL"""
    print(f"\n=== Transcribing Video ===")
    print(f"URL: {video_url}")
    print("Processing... (this may take a few minutes)")
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/transcribe",
            json={"url": video_url},
            timeout=3600  # 1 hour timeout for long videos
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"\n✓ Transcription successful!")
            print(f"\nTranscript ({len(result['transcript'])} characters):")
            print("-" * 80)
            print(result['transcript'][:500] + "..." if len(result['transcript']) > 500 else result['transcript'])
            print("-" * 80)
            return result
        else:
            print(f"ERROR: {response.status_code}")
            print(response.json())
            return None
            
    except requests.exceptions.Timeout:
        print("ERROR: Request timed out. Video may be too long.")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to API")
    except Exception as e:
        print(f"ERROR: {str(e)}")
    
    return None

if __name__ == "__main__":
    # Test health first
    if not test_health():
        print("\nPlease start the API with: python main.py")
        sys.exit(1)
    
    # Example videos to transcribe (you can modify these)
    test_videos = [
        # "https://www.youtube.com/watch?v=dQw4w9WgXcQ",  # Rick Roll (short)
        # Add your video URLs here
    ]
    
    if len(sys.argv) > 1:
        # If URL provided as command line argument
        video_url = sys.argv[1]
        transcribe_video(video_url)
    elif test_videos:
        # Otherwise use test videos
        for video in test_videos:
            transcribe_video(video)
    else:
        print("\nUsage: python client.py <video_url>")
        print("\nExample:")
        print('  python client.py "https://www.youtube.com/watch?v=dQw4w9WgXcQ"')
