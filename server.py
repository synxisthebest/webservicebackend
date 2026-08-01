import urllib.parse
import os
import json
import re
from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import yt_dlp
import requests

app = FastAPI(
    title="Glassmorphic Audio Streaming Proxy & Auto YouTube Engine",
    description="Backend proxy for ad-free audio streaming, youtube metadata extraction, and shared global database",
    version="3.2.0"
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

# Optimized yt-dlp Options for Cloud Datacenters (Bypasses YouTube Bot Detection & Rate-limits)
YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'quiet': True,
    'no_warnings': True,
    'extract_flat': False,
    'skip_download': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['android', 'web', 'mweb', 'ios'],
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
    }
}

def clean_input_query(query_str: str) -> str:
    unquoted = urllib.parse.unquote(query_str).strip()
    if not unquoted.startswith('http://') and not unquoted.startswith('https://'):
        return f"ytsearch1:{unquoted}"
    return unquoted

def extract_video_id(url_or_query: str) -> str:
    match = re.search(r'(?:v=|\/|be\/)([0-9A-Za-z_-]{11})', url_or_query)
    return match.group(1) if match else None

# Fix 405 Method Not Allowed for Render Health Checks (HEAD /)
@app.api_route("/", methods=["GET", "HEAD"])
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

# Endpoint for Global Playlist
@app.api_route("/playlist", methods=["GET", "HEAD"])
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

    video_id = extract_video_id(target_query)
    if video_id and not thumbnail:
        thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg"

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if info:
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]

                youtube_url = info.get('webpage_url') or info.get('url') or target_query
                title = info.get('title') or title or 'YouTube Track'
                artist = info.get('uploader') or info.get('channel') or artist or 'YouTube Artist'
                duration = info.get('duration') or duration

                extracted_id = info.get('id') or video_id
                if extracted_id:
                    thumbnail = f"https://i.ytimg.com/vi/{extracted_id}/hqdefault.jpg"
    except Exception as e:
        print("yt-dlp extract notice:", e)

    if not title:
        title = "YouTube Track"
    if not artist:
        artist = "YouTube Music"
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

@app.api_route("/track-info", methods=["GET", "HEAD"])
def get_track_info(url: str = Query(..., description="YouTube Video URL or Search Query")):
    target_query = clean_input_query(url)
    video_id = extract_video_id(target_query)
    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if info and 'entries' in info and len(info['entries']) > 0:
                info = info['entries'][0]

            if info:
                vid_id = info.get('id') or video_id
                if vid_id:
                    thumbnail = f"https://i.ytimg.com/vi/{vid_id}/hqdefault.jpg"

                return {
                    "id": vid_id,
                    "title": info.get('title', 'Unknown Title'),
                    "artist": info.get('uploader') or info.get('channel') or 'Unknown Artist',
                    "duration": info.get('duration', 0),
                    "thumbnail": thumbnail or info.get('thumbnail'),
                    "youtubeUrl": info.get('webpage_url') or target_query,
                    "audio_endpoint": f"/play-audio?url={urllib.parse.quote(info.get('webpage_url') or target_query)}"
                }
    except Exception as e:
        print("track-info notice:", e)

    return {
        "id": video_id or "yt-track",
        "title": "YouTube Track",
        "artist": "YouTube Music",
        "duration": 180,
        "thumbnail": thumbnail or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop",
        "youtubeUrl": target_query,
        "audio_endpoint": f"/play-audio?url={urllib.parse.quote(target_query)}"
    }

@app.api_route("/play-audio", methods=["GET", "HEAD"])
def play_audio(url: str = Query(..., description="YouTube Video URL or Query to Stream")):
    target_query = clean_input_query(url)
    
    player_clients = [
        ['android', 'web'],
        ['ios', 'mweb'],
        ['web']
    ]

    direct_audio_url = None
    last_error = None

    for client_list in player_clients:
        custom_opts = dict(YTDL_OPTIONS)
        custom_opts['extractor_args'] = {'youtube': {'player_client': client_list}}
        
        try:
            with yt_dlp.YoutubeDL(custom_opts) as ydl:
                info = ydl.extract_info(target_query, download=False)
                if info and 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]
                
                if info:
                    direct_audio_url = info.get('url')
                    if not direct_audio_url and 'formats' in info:
                        audio_formats = [f for f in info['formats'] if f.get('vcodec') == 'none' and f.get('acodec') != 'none']
                        if audio_formats:
                            audio_formats.sort(key=lambda x: x.get('tbr') or 0)
                            direct_audio_url = audio_formats[-1].get('url')
                        elif info['formats']:
                            direct_audio_url = info['formats'][-1].get('url')
                    
                    if direct_audio_url:
                        break
        except Exception as e:
            last_error = str(e)

    if direct_audio_url:
        return RedirectResponse(url=direct_audio_url, status_code=307)
    
    raise HTTPException(status_code=500, detail=f"Error streaming audio from YouTube: {last_error or 'Video unavailable or blocked'}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Glassmorphic Audio Proxy & Auto YouTube Engine on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
