import urllib.parse
import os
import json
import re
import time
import hashlib
from fastapi import FastAPI, HTTPException, Query, Body, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse, JSONResponse
import yt_dlp
import requests

app = FastAPI(
    title="Glassmorphic Audio Streaming Proxy & Bot-Bypass Engine",
    description="Backend proxy for ad-free audio streaming, youtube metadata extraction, github release parser and user auth manager",
    version="4.7.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_FILE = "shared_playlist.json"
USERS_FILE = "users.json"

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

DEFAULT_USERS = [
    {
        "username": "admin",
        "password_hash": hash_password("admin123"),
        "displayName": "Administrator",
        "role": "admin",
        "avatar": "https://api.dicebear.com/7.x/bottts/svg?seed=admin"
    }
]

DEFAULT_PLAYLIST = [
    {
        "id": "hit-1",
        "rank": "01",
        "title": "Starboy",
        "artist": "The Weeknd ft. Daft Punk",
        "thumbnail": "https://i.ytimg.com/vi/34Na4j8AVgA/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=34Na4j8AVgA",
        "duration": 230,
        "addedBy": "admin",
        "addedByDisplayName": "Administrator"
    },
    {
        "id": "hit-2",
        "rank": "02",
        "title": "Blinding Lights",
        "artist": "The Weeknd",
        "thumbnail": "https://i.ytimg.com/vi/4NRXx6U8ABQ/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=4NRXx6U8ABQ",
        "duration": 200,
        "addedBy": "admin",
        "addedByDisplayName": "Administrator"
    },
    {
        "id": "hit-3",
        "rank": "03",
        "title": "As It Was",
        "artist": "Harry Styles",
        "thumbnail": "https://i.ytimg.com/vi/H5v3kku4y6Q/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=H5v3kku4y6Q",
        "duration": 167,
        "addedBy": "admin",
        "addedByDisplayName": "Administrator"
    },
    {
        "id": "hit-4",
        "rank": "04",
        "title": "Shape of You",
        "artist": "Ed Sheeran",
        "thumbnail": "https://i.ytimg.com/vi/JGwWNGJdvx8/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=JGwWNGJdvx8",
        "duration": 233,
        "addedBy": "admin",
        "addedByDisplayName": "Administrator"
    },
    {
        "id": "hit-5",
        "rank": "05",
        "title": "Stay",
        "artist": "The Kid LAROI & Justin Bieber",
        "thumbnail": "https://i.ytimg.com/vi/kTJczUoc26U/hqdefault.jpg",
        "youtubeUrl": "https://www.youtube.com/watch?v=kTJczUoc26U",
        "duration": 141,
        "addedBy": "admin",
        "addedByDisplayName": "Administrator"
    }
]

def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return DEFAULT_USERS
    save_users(DEFAULT_USERS)
    return DEFAULT_USERS

def save_users(users_data):
    try:
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users_data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("Users save error:", e)

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
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'source_address': '0.0.0.0',
    'extractor_args': {
        'youtube': {
            'player_client': ['tvhtml5', 'android_embedded', 'mweb'],
            'skip': ['hls', 'dash']
        }
    },
    'http_headers': {
        'User-Agent': 'Mozilla/5.0 (SmartTV; Linux; Tizen 5.0) AppleWebKit/537.36 (KHTML, like Gecko) Version/5.0 TV Safari/537.36',
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

function_piped_cache = {}

def get_audio_stream_from_piped(video_id: str) -> str:
    if not video_id:
        return None

    if video_id in function_piped_cache:
        return function_piped_cache[video_id]

    piped_instances = [
        f"https://api.piped.video/streams/{video_id}",
        f"https://pipedapi.kavin.rocks/streams/{video_id}",
        f"https://invidious.privacydev.net/api/v1/videos/{video_id}"
    ]

    for endpoint in piped_instances:
        try:
            res = requests.get(endpoint, timeout=4)
            if res.status_code == 200:
                data = res.json()
                audio_streams = data.get('audioStreams') or data.get('adaptiveFormats')
                if audio_streams:
                    audio_only = [s for s in audio_streams if 'audio' in s.get('mimeType', '') or s.get('type') == 'audio']
                    target_list = audio_only if audio_only else audio_streams
                    target_list.sort(key=lambda x: x.get('bitrate', 0), reverse=True)
                    stream_url = target_list[0].get('url')
                    if stream_url:
                        function_piped_cache[video_id] = stream_url
                        return stream_url
        except Exception:
            continue

    return None

def fetch_github_release_tracks(release_url: str):
    match = re.search(r'github\.com\/([^\/]+)\/([^\/]+)\/releases\/tag\/([^\/]+)', release_url)
    if not match:
        return []

    owner = match.group(1)
    repo = match.group(2)
    tag = match.group(3)

    expanded_url = f"https://github.com/{owner}/{repo}/releases/expanded_assets/{tag}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    try:
        res = requests.get(expanded_url, headers=headers, timeout=6)
        if res.status_code == 200:
            matches = re.findall(r'href="([^"]+/releases/download/[^"]+)"', res.text)
            unique_links = list(set(matches))
            tracks = []
            for idx, link in enumerate(sorted(unique_links)):
                full_url = "https://github.com" + link if link.startswith('/') else link
                raw_filename = full_url.split('/')[-1]
                clean_name = urllib.parse.unquote(raw_filename)
                clean_name = re.sub(r'\.(flac|mp3|wav|m4a|ogg)$', '', clean_name, flags=re.IGNORECASE).replace('.', ' ')
                
                tracks.append({
                    "id": f"gh-{tag}-{idx+1}",
                    "title": clean_name,
                    "artist": f"{owner} (GitHub Release)",
                    "audioUrl": full_url,
                    "thumbnail": "https://images.unsplash.com/photo-1514525253161-7a46d19cd819?q=80&w=400&auto=format&fit=crop",
                    "duration": 210,
                    "plays": "GitHub FLAC Stream",
                    "isDirectUrl": True
                })
            return tracks
    except Exception as e:
        print("GitHub release parse error:", e)

    return []

def fetch_youtube_metadata_server(query_or_url: str):
    target_query = clean_input_query(query_or_url)
    video_id = extract_video_id(target_query)
    title = None
    artist = None
    thumbnail = f"https://i.ytimg.com/vi/{video_id}/hqdefault.jpg" if video_id else None
    duration = 180
    webpage_url = f"https://www.youtube.com/watch?v={video_id}" if video_id else target_query

    if video_id:
        try:
            oembed_url = f"https://www.youtube.com/oembed?url={urllib.parse.quote(webpage_url)}&format=json"
            oembed_res = requests.get(oembed_url, timeout=3)
            if oembed_res.status_code == 200:
                odata = oembed_res.json()
                title = odata.get("title")
                artist = odata.get("author_name")
                if odata.get("thumbnail_url"):
                    thumbnail = odata.get("thumbnail_url")
        except Exception:
            pass

    try:
        with yt_dlp.YoutubeDL(YTDL_OPTIONS) as ydl:
            info = ydl.extract_info(target_query, download=False)
            if info:
                if 'entries' in info and len(info['entries']) > 0:
                    info = info['entries'][0]
                if not title:
                    title = info.get('title')
                if not artist:
                    artist = info.get('uploader') or info.get('channel')
                if info.get('duration'):
                    duration = info.get('duration')
                if info.get('webpage_url'):
                    webpage_url = info.get('webpage_url')
                vid = info.get('id') or video_id
                if vid and not thumbnail:
                    thumbnail = f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg"
    except Exception as e:
        print("yt-dlp extract notice:", e)

    if not title:
        title = target_query if not target_query.startswith("http") else "YouTube Track"
    if not artist:
        artist = "YouTube Music"
    if not thumbnail:
        thumbnail = "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop"

    return {
        "id": video_id or ("yt-" + str(int(time.time()))),
        "title": title,
        "artist": artist,
        "thumbnail": thumbnail,
        "duration": duration,
        "youtubeUrl": webpage_url,
        "videoId": video_id
    }

# ================= AUTHENTICATION ENDPOINTS =================

@app.post("/register")
def register_account(payload: dict = Body(...)):
    username = payload.get("username", "").strip().lower()
    password = payload.get("password", "").strip()
    display_name = payload.get("displayName", "").strip() or username

    if not username or not password:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")

    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Tên đăng nhập phải có ít nhất 3 ký tự")

    users = load_users()
    if any(u["username"] == username for u in users):
        raise HTTPException(status_code=400, detail="Tên đăng nhập này đã được sử dụng")

    new_user = {
        "username": username,
        "password_hash": hash_password(password),
        "displayName": display_name,
        "role": "user",
        "avatar": f"https://api.dicebear.com/7.x/bottts/svg?seed={username}"
    }
    users.append(new_user)
    save_users(users)

    return {
        "status": "success",
        "message": f"Tạo tài khoản @{username} thành công!",
        "user": {
            "username": new_user["username"],
            "displayName": new_user["displayName"],
            "role": new_user["role"],
            "avatar": new_user["avatar"]
        }
    }

@app.post("/login")
def login_account(payload: dict = Body(...)):
    username = payload.get("username", "").strip().lower()
    password = payload.get("password", "").strip()

    if not username or not password:
        raise HTTPException(status_code=400, detail="Vui lòng nhập đầy đủ tên đăng nhập và mật khẩu")

    users = load_users()
    target_user = next((u for u in users if u["username"] == username), None)
    if not target_user:
        raise HTTPException(status_code=401, detail="Tài khoản không tồn tại")

    if target_user["password_hash"] != hash_password(password):
        raise HTTPException(status_code=401, detail="Mật khẩu không chính xác")

    return {
        "status": "success",
        "message": f"Đăng nhập thành công! Chào mừng @{target_user['username']}",
        "user": {
            "username": target_user["username"],
            "displayName": target_user.get("displayName", target_user["username"]),
            "role": target_user.get("role", "user"),
            "avatar": target_user.get("avatar", f"https://api.dicebear.com/7.x/bottts/svg?seed={username}")
        }
    }

@app.get("/users")
def get_user_list():
    users = load_users()
    return [
        {
            "username": u["username"],
            "displayName": u.get("displayName", u["username"]),
            "role": u.get("role", "user"),
            "avatar": u.get("avatar", f"https://api.dicebear.com/7.x/bottts/svg?seed={u['username']}")
        }
        for u in users
    ]

# ================= PLAYLIST & TRACK ENDPOINTS =================

@app.api_route("/", methods=["GET", "HEAD"])
def read_root():
    return {
        "status": "online",
        "service": "Glassmorphic Audio Streaming Proxy & Auth Engine",
        "endpoints": {
            "play_audio": "/play-audio?url=[ENCODED_YOUTUBE_URL_OR_QUERY]",
            "track_info": "/track-info?url=[ENCODED_YOUTUBE_URL_OR_QUERY]",
            "github_release": "/github-release?url=[ENCODED_GITHUB_RELEASE_URL]",
            "get_playlist": "/playlist",
            "add_track": "/add-track",
            "edit_track": "/edit-track",
            "delete_track": "/delete-track",
            "login": "/login",
            "register": "/register"
        }
    }

@app.api_route("/playlist", methods=["GET", "HEAD"])
def get_global_playlist():
    playlist = load_db()
    return {"status": "success", "playlist": playlist}

@app.api_route("/github-release", methods=["GET", "HEAD"])
def parse_github_release(url: str = Query(..., description="GitHub Release Tag URL")):
    tracks = fetch_github_release_tracks(url)
    return {"status": "success", "count": len(tracks), "tracks": tracks}

@app.post("/add-track")
def add_track_to_global_playlist(payload: dict = Body(...)):
    raw_query = payload.get("youtubeUrl") or payload.get("url") or payload.get("query")
    if not raw_query:
        raise HTTPException(status_code=400, detail="Missing youtubeUrl or query parameter")

    added_by = payload.get("addedBy") or "admin"
    added_by_display = payload.get("addedByDisplayName") or added_by

    if "github.com" in raw_query and "/releases/tag/" in raw_query:
        gh_tracks = fetch_github_release_tracks(raw_query)
        if gh_tracks:
            playlist = load_db()
            for t in gh_tracks:
                t["addedBy"] = added_by
                t["addedByDisplayName"] = added_by_display
                playlist = [p for p in playlist if p.get('id') != t['id']]
                playlist.insert(0, t)
            save_db(playlist)
            return {"status": "success", "message": f"Đã nạp {len(gh_tracks)} bài từ GitHub Release!", "playlist": playlist, "tracks": gh_tracks}

    meta = fetch_youtube_metadata_server(raw_query)

    title = payload.get("title") or meta["title"]
    artist = payload.get("artist") or meta["artist"]
    thumbnail = payload.get("thumbnail") or meta["thumbnail"]
    duration = payload.get("duration") or meta["duration"]
    youtube_url = meta["youtubeUrl"]

    new_item = {
        "id": payload.get("id") or ("global-" + str(int(time.time() * 1000))),
        "title": title,
        "artist": artist,
        "thumbnail": thumbnail,
        "youtubeUrl": youtube_url,
        "duration": duration,
        "addedBy": added_by,
        "addedByDisplayName": added_by_display
    }

    playlist = load_db()
    playlist = [p for p in playlist if p.get('youtubeUrl') != youtube_url and p.get('id') != new_item['id']]
    playlist.insert(0, new_item)

    save_db(playlist)
    return {"status": "success", "message": "Bài hát đã được nạp tự động thành công!", "track": new_item, "playlist": playlist}

@app.put("/edit-track")
def edit_track(payload: dict = Body(...)):
    track_id = payload.get("id") or payload.get("trackId")
    username = payload.get("username", "admin").strip().lower()

    if not track_id:
        raise HTTPException(status_code=400, detail="Thiếu thông tin bài hát")

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    user_role = user.get("role") if user else ("admin" if username == "admin" else "user")

    playlist = load_db()
    target_idx = next((i for i, p in enumerate(playlist) if p.get("id") == track_id), -1)

    if target_idx == -1:
        new_track = {
            "id": track_id,
            "title": payload.get("title", "").strip() or "Track Title",
            "artist": payload.get("artist", "").strip() or "Artist Name",
            "thumbnail": payload.get("thumbnail", "").strip() or "https://images.unsplash.com/photo-1511671782779-c97d3d27a1d4?q=80&w=400&auto=format&fit=crop",
            "youtubeUrl": payload.get("youtubeUrl", "").strip() or "",
            "duration": payload.get("duration", 180),
            "addedBy": username,
            "addedByDisplayName": user.get("displayName") if user else username
        }
        playlist.insert(0, new_track)
        save_db(playlist)
        return {"status": "success", "message": "Đã thêm & chỉnh sửa bài hát vào danh sách!", "track": new_track, "playlist": playlist}

    target_track = playlist[target_idx]
    added_by = target_track.get("addedBy", "")

    if added_by and added_by.lower() != username and user_role != "admin":
        raise HTTPException(status_code=403, detail="Bạn không có quyền chỉnh sửa bài hát này (chỉ tác giả hoặc Admin mới có quyền)")

    if payload.get("title"):
        target_track["title"] = payload["title"].strip()
    if payload.get("artist"):
        target_track["artist"] = payload["artist"].strip()
    if payload.get("thumbnail"):
        target_track["thumbnail"] = payload["thumbnail"].strip()
    if payload.get("youtubeUrl"):
        target_track["youtubeUrl"] = payload["youtubeUrl"].strip()

    playlist[target_idx] = target_track
    save_db(playlist)
    return {"status": "success", "message": "Cập nhật bài hát thành công!", "track": target_track, "playlist": playlist}

@app.post("/delete-track")
def delete_track(payload: dict = Body(...)):
    track_id = payload.get("id") or payload.get("trackId")
    username = payload.get("username", "admin").strip().lower()

    if not track_id:
        raise HTTPException(status_code=400, detail="Thiếu thông tin bài hát")

    users = load_users()
    user = next((u for u in users if u["username"] == username), None)
    user_role = user.get("role") if user else ("admin" if username == "admin" else "user")

    playlist = load_db()
    target_track = next((p for p in playlist if p.get("id") == track_id), None)

    if target_track:
        added_by = target_track.get("addedBy", "")
        if added_by and added_by.lower() != username and user_role != "admin":
            raise HTTPException(status_code=403, detail="Bạn không có quyền xóa bài hát này (chỉ tác giả hoặc Admin mới có quyền)")

    playlist = [p for p in playlist if p.get("id") != track_id]
    save_db(playlist)
    return {"status": "success", "message": "Đã xóa bài hát khỏi danh sách!", "playlist": playlist}

@app.api_route("/track-info", methods=["GET", "HEAD"])
def get_track_info(url: str = Query(..., description="YouTube Video URL or Search Query")):
    meta = fetch_youtube_metadata_server(url)
    meta["audio_endpoint"] = f"/play-audio?url={urllib.parse.quote(meta['youtubeUrl'])}"
    return meta

@app.api_route("/play-audio", methods=["GET", "HEAD"])
def play_audio(url: str = Query(..., description="YouTube Video URL or Query to Stream")):
    target_query = clean_input_query(url)
    video_id = extract_video_id(target_query)

    if video_id:
        piped_url = get_audio_stream_from_piped(video_id)
        if piped_url:
            return RedirectResponse(url=piped_url, status_code=307)

    player_clients = [
        ['android', 'ios'],
        ['tvhtml5', 'android_embedded'],
        ['mweb', 'web']
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

    raise HTTPException(status_code=500, detail=f"Error streaming audio: {last_error or 'Video stream unavailable'}")

if __name__ == "__main__":
    import uvicorn
    print("Starting Glassmorphic Audio Proxy & Auth Server on http://127.0.0.1:8000 ...")
    uvicorn.run("server:app", host="127.0.0.1", port=8000, reload=True)
