import json
import urllib.request
import re

def get_android_caption(video_id: str):
    url = "https://www.youtube.com/youtubei/v1/player"
    payload = {
        "videoId": video_id,
        "context": {
            "client": {
                "clientName": "ANDROID",
                "clientVersion": "19.29.37",
                "androidSdkVersion": 34,
                "hl": "pt",
                "gl": "BR"
            }
        }
    }
    
    post_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=post_data,
        headers={
            "Content-Type": "application/json",
            "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 14; pt_BR; Pixel 7)"
        }
    )

    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
        print(f"Android Player API encontrou {len(captions)} trilhas de legenda.")

        for track in captions:
            lang = track.get("languageCode")
            name = track.get("name", {}).get("runs", [{}])[0].get("text", "")
            base_url = track.get("baseUrl")
            print(f" -> Lang: {lang} | Name: {name} | URL: {base_url[:80]}...")

            if lang in ["pt", "pt-BR"] or not captions:
                # Baixar legenda via Android timedtext URL
                sub_url = base_url + "&fmt=json3"
                sub_req = urllib.request.Request(
                    sub_url,
                    headers={
                        "User-Agent": "com.google.android.youtube/19.29.37 (Linux; U; Android 14; pt_BR; Pixel 7)"
                    }
                )
                with urllib.request.urlopen(sub_req) as sub_resp:
                    sub_json = json.loads(sub_resp.read().decode("utf-8"))
                    
                lines = []
                for ev in sub_json.get("events", []):
                    segs = ev.get("segs", [])
                    t = "".join([s.get("utf8", "") for s in segs if "utf8" in s]).strip()
                    if t and t != "\n":
                        lines.append(t)
                
                clean_text = "\n".join(lines)
                print(f"🎉 SUCESSO ABSOLUTO! Total de linhas: {len(lines)} | Palavras: {len(clean_text.split())}")
                print("Amostra:")
                print("\n".join(lines[:10]))
                return clean_text

    except Exception as e:
        print(f"Erro no Android Player API: {type(e).__name__} - {e}")
        return None

if __name__ == "__main__":
    get_android_caption("Yx99q0tSxHM")
