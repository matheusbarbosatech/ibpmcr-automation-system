import json
import re
import urllib.request
import http.cookiejar

def load_cookies():
    cookie_jar = http.cookiejar.MozillaCookieJar('cookies.txt')
    try:
        cookie_jar.load(ignore_discard=True, ignore_expires=True)
        print("Cookies.txt carregados com sucesso!")
        return cookie_jar
    except Exception as e:
        print(f"Erro ao carregar cookies: {e}")
        return None

def fetch_direct_transcript(video_id: str):
    cj = load_cookies()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj)) if cj else urllib.request.build_opener()
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "Referer": f"https://www.youtube.com/watch?v={video_id}",
        "Origin": "https://www.youtube.com"
    }

    url = f"https://www.youtube.com/watch?v={video_id}"
    req = urllib.request.Request(url, headers=headers)
    
    with opener.open(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});(?:var\s+|</script>)', html)
    if not match:
        print("ytInitialPlayerResponse não encontrado no HTML")
        return None

    player_data = json.loads(match.group(1))
    captions = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
    print(f"Trilhas de legenda encontradas: {len(captions)}")

    pt_track = None
    for track in captions:
        lang = track.get("languageCode", "")
        print(f" - Idioma: {lang} | Name: {track.get('name', {}).get('simpleText')} | Kind: {track.get('kind', '')}")
        if lang in ["pt", "pt-BR"] and not pt_track:
            pt_track = track

    if not pt_track and captions:
        pt_track = captions[0]

    if not pt_track:
        print("Nenhuma trilha encontrada.")
        return None

    base_url = pt_track["baseUrl"]
    if "&fmt=" not in base_url:
        base_url += "&fmt=json3"

    print(f"Baixando legenda via timedtext URL com cookies...")
    sub_req = urllib.request.Request(base_url, headers=headers)
    with opener.open(sub_req) as s_resp:
        content = s_resp.read().decode('utf-8', errors='ignore')
        sub_json = json.loads(content)

    lines = []
    events = sub_json.get("events", [])
    for event in events:
        segs = event.get("segs", [])
        text = "".join([s.get("utf8", "") for s in segs if "utf8" in s]).strip()
        if text and text != "\n":
            lines.append(text)

    clean_text = "\n".join(lines)
    print(f"✅ SUCESSO! Total de linhas: {len(lines)} | Palavras: {len(clean_text.split())}")
    print("Amostra dos primeiros parágrafos:")
    print("\n".join(lines[:10]))
    return clean_text

if __name__ == "__main__":
    fetch_direct_transcript("Yx99q0tSxHM")
