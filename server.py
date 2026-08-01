import urllib.parse
import os
import json
import re
from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import yt_dlp
import requests

app = FastAPI(
    title="Glassmorphic Audio Streaming Proxy & Youtube Engine",
    description="Backend proxy for ad-free audio streaming, youtube metadata extraction, and shared global database",
    version="3.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "shared_playlist.json"

DEFAULT_PLAYLIST = [
    {
        "id": "hit-1",
        "rank": "01",
        "title": "Starboy",
        "artist": "The Weeknd ft. Daft Punk",
        "thumbnail": "https://i.ytimg.com/vi/34Na4j8AVgA/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=34Na4j8AVgA",
        "duration": 230
    },
    {
        "id": "hit-2",
        "rank": "02",
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=4NRXx6U8ABQ",
        "duration": 200
    },
    {
        "id": "hit-3",
        "rank": "03",
        "title": "As It Was",
        "artist": "Harry Styles",
        "thumbnail": "https://i.ytimg.com/vi/H5v3kku4y6Q/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=H5v3kku4y6Q",
        "duration": 167
    },
    {
        "id": "hit-4",
        "rank": "04",
        "title": "Shape of You",
        "artist": "Ed Sheeran",
        "thumbnail": "https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
        "duration": 233
    },
    {
        "id": "hit-5",
        "rank": "05",
        "title": "Stay",
        "artist": "The Kid LAROI & Justin Bieber",
        "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg",
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

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
}

def clean_input_query(query_str: str) -> str:
    unquoted = urllib.parse.unquote(query_str).strip()
    if not unquoted.startswith('http://') and not unquoted.startswith('https://'):
        return f"ytsearch1:{unquoted}"
    return unquoted

@app.get("/")
def read_root():
    return {
        "status": "online",
        "service": "Glassmorphic Audio Streaming Proxy & Auto YouTube Engine",
        "endpoints": {
            "play_audio": "/play-audio?url=[ENCODED_YOUTUBE_URL_OR_QUERY]",
            "track_info": "/track-info?url=[ENCODED_YOUTUBE_URL_OR_QUERY]",
            "get_playlist": "/playlist",
            "add_track": "/add-track"
        }
    }

@app.get("/playlist")
def get_global_playlist():
    playlist = load_db()
    return {"status": "success", "playlist": playlist}

@app.post("/add-track")
def add_track_to_global_playlist(payload: dict = Body(...)):
    raw_query = payload.get("youtubeUrl") or payload.get("url") or payload.get("query")
    if not raw_query:
        raise HTTPException(status_code=400, detail="Missing youtubeUrl or query parameter")

    target_query = clean_input_query(raw_query)
    title = payload.get("title")
    artist = payload.get("artist")
    thumbnail = payload.get("thumbnail")
    duration = payload.get("duration", 180)
    youtube_url = target_query

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            youtube_url = info.get('webpage_url') or info.get('url') or target_query
            title = info.get('title') or title or 'YouTube Track'
            artist = info.get('uploader') or info.get('channel') or artist or 'YouTube Artist'
            duration = info.get('duration') or duration

            # Exact YouTube Thumbnail Extraction
            video_id = info.get('id')
            if video_id:
                thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"
            else:
                thumbnails = info.get('thumbnails', [])
                if thumbnails:
                    thumbnail = thumbnails[-1].get('url')
    except Exception as e:
        print("yt-dlp extract notice:", e)

    if not thumbnail:
        thumbnail = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop"

    new_item = {
        "id": "global-" + str(int(os.times().system * 1000)),
        "title": title,
        "artist": artist,
        "thumbnail": thumbnail,
        "youtubeUrl": youtube_url,
        "duration": duration
    }

    playlist = load_db()
    playlist = [p for p in playlist if p.get('youtubeUrl') != youtube_url]
    playlist.insert(0, new_item)

    save_db(playlist)
    return {"status": "success", "message": "Track auto-extracted and added to global playlist!", "track": new_item, "playlist": playlist}

@app.get("/track-info")
def get_track_info(url: str = Query(..., description="YouTube Video URL or Search Query")):
    target_query = clean_input_query(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            video_id = info.get('id')
            thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else info.get('thumbnail')

            return {
                "id": video_id,
                "title": info.get('title', 'Unknown Title'),
                "artist": info.get('uploader') or info.get('channel') or 'Unknown Artist',
                "duration": info.get('duration', 0),
                "thumbnail": thumbnail,
                "youtubeUrl": info.get('webpage_url') or target_query,
                "audio_endpoint": f"/play-audio?url={urllib.parse.quote(info.get('webpage_url') or target_query)}"
            }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch YouTube info: {str(e)}")

@app.get("/play-audio")
def play_audio(url: str = Query(..., description="YouTube Video URL or Query to Stream")):
    target_query = clean_input_query(url)
    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]
            
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
    print("Starting Glassmorphic Audio Proxy & Auto YouTube Engine on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
