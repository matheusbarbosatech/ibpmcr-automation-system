import http.cookiejar
import json
import requests
import yt_dlp

def fetch_caption_via_ytdlp(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    ydl_opts = {
        'skip_download': True,
        'quiet': True,
        'no_warnings': True,
        'cookiefile': 'cookies.txt'
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        try:
            info = ydl.extract_info(url, download=False)
        except Exception as e:
            print(f"Erro ao extrair info do vídeo: {e}")
            return None

    auto_caps = info.get("automatic_captions", {})
    subtitles = info.get("subtitles", {})

    print(f"Subtitles manuais: {list(subtitles.keys())}")
    print(f"Legendas automáticas: {list(auto_caps.keys())}")

    pt_tracks = subtitles.get("pt") or subtitles.get("pt-BR") or auto_caps.get("pt") or auto_caps.get("pt-BR") or auto_caps.get("pt-orig")

    if not pt_tracks:
        print("Nenhuma trilha em português encontrada.")
        return None

    sub_url = None
    for track in pt_tracks:
        ext = track.get("ext")
        if ext == "json3":
            sub_url = track.get("url")
            break
        elif ext == "vtt" and not sub_url:
            sub_url = track.get("url")

    if not sub_url and pt_tracks:
        sub_url = pt_tracks[0].get("url")

    print(f"URL de legenda encontrada: {sub_url[:100]}...")

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Referer": f"https://www.youtube.com/watch?v={video_id}"
    })

    cj = http.cookiejar.MozillaCookieJar('cookies.txt')
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cj)
        print("Cookies.txt vinculados à requisição HTTP.")
    except Exception as e:
        print(f"Aviso cookie: {e}")

    resp = session.get(sub_url)
    print(f"HTTP Status com cookies: {resp.status_code}")

    if resp.status_code == 200:
        try:
            sub_json = resp.json()
            lines = []
            for event in sub_json.get("events", []):
                segs = event.get("segs", [])
                text = "".join([s.get("utf8", "") for s in segs if "utf8" in s]).strip()
                if text and text != "\n":
                    lines.append(text)
            clean_text = "\n".join(lines)
            print(f"🎉 SUCESSO ABSOLUTO! Total de linhas: {len(lines)} | Palavras: {len(clean_text.split())}")
            print("Amostra dos primeiros parágrafos:")
            print("\n".join(lines[:10]))
            return clean_text
        except Exception as e:
            print("Resposta não é JSON3 puro, texto bruto:")
            print(resp.text[:300])
            return resp.text
    else:
        print("Ainda retornou erro:", resp.status_code, resp.text[:200])

    return None

if __name__ == "__main__":
    fetch_caption_via_ytdlp("JZqi2LW0Jmw")
