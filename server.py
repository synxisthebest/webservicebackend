import urllib.parse
import os
import json
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import yt_dlp
import requests

app = FastAPI(
    title="Glassmorphic Audio Streaming Proxy & Shared Database",
    description="Backend proxy for audio streaming and shared global playlist database",
    version="2.0.0"
)

# Enable CORS for frontend execution from GitHub Pages and anywhere
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to store shared global playlist JSON file on server
DB_FILE = "shared_playlist.json"

# Default hit tracks if database is fresh
DEFAULT_PLAYLIST = [
    {
        "id": "hit-1",
        "rank": "01",
        "title": "Starboy",
        "artist": "The Weeknd ft. Daft Punk",
        "thumbnail": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": "https://www.youtube.com/watch?v=34Na4j8AVgA",
        "duration": 230
    },
    {
        "id": "hit-2",
        "rank": "02",
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "thumbnail": "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": "https://www.youtube.com/watch?v=4NRXx6U8ABQ",
        "duration": 200
    },
    {
        "id": "hit-3",
        "rank": "03",
        "title": "As It Was",
        "artist": "Harry Styles",
        "thumbnail": "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": "https://www.youtube.com/watch?v=H5v3kku4y6Q",
        "duration": 167
    },
    {
        "id": "hit-4",
        "rank": "04",
        "title": "Shape of You",
        "artist": "Ed Sheeran",
        "thumbnail": "https://images.unsplash.com/photo-1470225620780-dba8ba36b745?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
        "duration": 233
    },
    {
        "id": "hit-5",
        "rank": "05",
        "title": "Stay",
        "artist": "The Kid LAROI & Justin Bieber",
        "thumbnail": "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": "https://www.youtube.com/watch?v=kTJczUoc26U",
        "duration": 141
    }
]

def load_db():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_PLAYLIST
    return DEFAULT_PLAYLIST

def save_db(playlist_data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(playlist_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("DB save error:", e)

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
    return urllib.parse.unquote(url)

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Glassmorphic Audio Streaming Proxy & Shared Database",
        "endpoints": {
            "play_audio": "/play-audio?url=[ENCODED_YOUTUBE_URL]",
            "track_info": "/track-info?url=[ENCODED_YOUTUBE_URL]",
            "get_playlist": "/playlist",
            "add_track": "/add-track"
        }
    }

@app.get("/playlist")
def get_global_playlist():
    """Returns the shared global playlist visible to all users worldwide."""
    playlist = load_db()
    return {"status": "success", "playlist": playlist}

@app.post("/add-track")
def add_track_to_global_playlist(payload: dict = Body(...)):
    """
    Saves a user-submitted track to the shared global database server.
    Payload format: { "youtubeUrl": "...", "title": "...", "artist": "..." }
    """
    raw_url = payload.get("youtubeUrl") or payload.get("url")
    if not raw_url:
        raise HTTPException(status_code=400, detail="Missing youtubeUrl parameter")

    target_url = clean_youtube_url(raw_url)
    title = payload.get("title")
    artist = payload.get("artist")
    thumbnail = payload.get("thumbnail")
    duration = payload.get("duration", 180)

    # Extract info via yt-dlp if metadata is incomplete
    if not title or not thumbnail:
        try:
            with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
                info = ydl.extract_info(target_url, download=False)
                title = title or info.get('title', 'YouTube Track')
                artist = artist or info.get('uploader') or info.get('channel') or 'YouTube Artist'
                duration = info.get('duration', duration)
                
                thumbnails = info.get('thumbnails', [])
                best_thumb = info.get('thumbnail')
                if thumbnails:
                    best_thumb = thumbnails[-1].get('url', best_thumb)
                thumbnail = thumbnail or best_thumb
        except Exception:
            title = title or 'YouTube Track'
            artist = artist or 'YouTube Music'
            thumbnail = thumbnail or 'https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop'

    new_item = {
        "id": "global-" + str(int(os.times().system * 1000)),
        "title": title,
        "artist": artist,
        "thumbnail": thumbnail,
        "youtubeUrl": target_url,
        "duration": duration
    }

    playlist = load_db()
    # Filter out duplicate URLs
    playlist = [p for p in playlist if p.get('youtubeUrl') != target_url]
    playlist.insert(0, new_item)

    save_db(playlist)
    return {"status": "success", "message": "Track added to global playlist for all users!", "track": new_item, "playlist": playlist}

@app.get("/track-info")
def get_track_info(url: str = Query(..., description="YouTube video URL")):
    target_url = clean_youtube_url(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_url, download=False)
            thumbnails = info.get('thumbnails', [])
            best_thumb = info.get('thumbnail')
            if thumbnails:
                best_thumb = thumbnails[-1].get('url', best_thumb)

            return {
                "id": info.get('id'),
                "title": info.get('title', 'Unknown Title'),
                "artist": info.get('uploader') or info.get('channel') or 'Unknown Artist',
                "duration": info.get('duration', 0),
                "thumbnail": best_thumb,
                "url": target_url,
                "audio_endpoint": f"/play-audio?url={urllib.parse.quote(target_url)}"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to process YouTube URL: {str(e)}")

@app.get("/play-audio")
def play_audio(url: str = Query(..., description="YouTube video URL to stream")):
    target_url = clean_youtube_url(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_url, download=False)
            
            direct_audio_url = info.get('url')
            if not direct_audio_url and 'formats' in info:
                audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                if audio_formats:
                    audio_formats.sort(key=lambda x: x.get('tbr') or 0)
                    direct_audio_url = audio_formats[-1].get('url')
                elif info['formats']:
                    direct_audio_url = info['formats'][-1].get('url')

            if not direct_audio_url:
                raise HTTPException(status_code=404, detail="Audio stream URL could not be extracted.")

            return RedirectResponse(url=direct_audio_url, status_code=307)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error streaming audio: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Glassmorphic Audio Proxy & Shared Database on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
