import yt_dlp
import json

url = "https://www.youtube.com/@ibpmcr7976/streams"
ydl_opts = {
    'extract_flat': 'in_playlist',
    'skip_download': True,
    'quiet': True
}

with yt_dlp.YoutubeDL(ydl_opts) as ydl:
    info = ydl.extract_info(url, download=False)
    entries = info.get('entries', [])
    print(f"Total de streams encontrados: {len(entries)}")
    for e in list(entries)[:5]:
        print(f"ID: {e.get('id')} | Título: {e.get('title')}")
