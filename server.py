import urllib.parse
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse, StreamingResponse
import yt_dlp
import requests
import re

app = FastAPI(
    title="Glassmorphic Audio Streaming Proxy",
    description="Backend proxy for extracting and streaming audio from YouTube URLs using yt-dlp",
    version="1.0.0"
)

# Enable CORS for local frontend execution
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# yt-dlp configuration options
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
}

def clean_youtube_url(url: str) -> str:
    """Unquote and clean incoming URL string."""
    unquoted = urllib.parse.unquote(url)
    # Extract standard YouTube video ID or URL format if embedded inside extra query params
    return unquoted

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Glassmorphic Audio Streaming Proxy",
        "endpoints": {
            "play_audio": "/play-audio?url=[ENCODED_YOUTUBE_URL]",
            "track_info": "/track-info?url=[ENCODED_YOUTUBE_URL]"
        }
    }

@app.get("/track-info")
def get_track_info(url: str = Query(..., description="YouTube video URL")):
    """Extract metadata (title, artist, thumbnail, duration) for a YouTube video."""
    target_url = clean_youtube_url(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            # Find best thumbnail
            thumbnails = info.get('thumbnails', [])
            best_thumb = info.get('thumbnail')
            if thumbnails:
                best_thumb = thumbnails[-1].get('url', best_thumb)

            stream_url = info.get('url')
            if not stream_url and 'formats' in info:
                # Find best audio format
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    stream_url = audio_formats[-1].get('url')
                elif info['formats']:
                    stream_url = info['formats'][-1].get('url')

            return {
                "id": info.get('id'),
                "title": info.get('title', 'Unknown Title'),
                "artist": info.get('uploader') or info.get('channel') or info.get('artist', 'Unknown Artist'),
                "duration": info.get('duration', 0),
                "thumbnail": best_thumb,
                "url": target_url,
                "stream_url": stream_url,
                "audio_endpoint": f"/play-audio?url={urllib.parse.quote(target_url)}"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process YouTube URL: {str(e)}")

@app.get("/play-audio")
def play_audio(url: str = Query(..., description="YouTube video URL to stream")):
    """
    Extracts the direct audio stream URL and redirects/proxies the audio stream.
    Directly compatible with HTML5 <audio src="http://127.0.0.1:8000/play-audio?url=...">
    """
    target_url = clean_youtube_url(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            direct_audio_url = info.get('url')
            if not direct_audio_url and 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    # Pick highest bitrate audio
                    audio_formats.sort(key=lambda x: x.get('tbr') or 0)
                    direct_audio_url = audio_formats[-1].get('url')
                elif info['formats']:
                    direct_audio_url = info['formats'][-1].get('url')

            if not direct_audio_url:
                raise HTTPException(status_code=404, detail="Audio stream URL could not be extracted.")

            # Redirect to direct audio stream
            return RedirectResponse(url=direct_audio_url, status_code=307)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error streaming audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Glassmorphic Audio Proxy on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
