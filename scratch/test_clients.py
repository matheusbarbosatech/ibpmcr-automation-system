import json
import urllib.request

def test_clients(video_id: str):
    clients = [
        {"clientName": "WEB", "clientVersion": "2.20240815.00.00", "hl": "pt", "gl": "BR"},
        {"clientName": "MWEB", "clientVersion": "2.20240815.00.00", "hl": "pt", "gl": "BR"},
        {"clientName": "ANDROID_TESTSUITE", "clientVersion": "1.9", "hl": "pt", "gl": "BR"},
        {"clientName": "TVHTML5", "clientVersion": "7.20240815.00.00", "hl": "pt", "gl": "BR"}
    ]

    for c in clients:
        c_name = c["clientName"]
        url = "https://www.youtube.com/youtubei/v1/player"
        payload = {
            "videoId": video_id,
            "context": {
                "client": c
            }
        }
        
        post_data = json.dumps(payload).encode("utf-8")
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36"
        }

        req = urllib.request.Request(url, data=post_data, headers=headers)

        try:
            with urllib.request.urlopen(req) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            
            captions = data.get("captions", {}).get("playerCaptionsTracklistRenderer", {}).get("captionTracks", [])
            print(f"[{c_name}] Status: OK | Captações: {len(captions)}")
            for tr in captions:
                print(f"  -> Lang: {tr.get('languageCode')} | Name: {tr.get('name', {}).get('simpleText') or tr.get('name', {}).get('runs', [{}])[0].get('text')}")
                
            if captions:
                base_url = captions[0]["baseUrl"] + "&fmt=json3"
                s_req = urllib.request.Request(base_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
                try:
                    with urllib.request.urlopen(s_req) as s_resp:
                        sub_json = json.loads(s_resp.read().decode("utf-8"))
                    events = sub_json.get("events", [])
                    print(f"  --> SUCESSO ABSOLUTO! Total de eventos de legenda: {len(events)}")
                    return c_name, sub_json
                except Exception as ex:
                    print(f"  --> Subtitle download error: {ex}")
        except Exception as e:
            print(f"[{c_name}] Erro: {e}")

if __name__ == "__main__":
    test_clients("Yx99q0tSxHM")
