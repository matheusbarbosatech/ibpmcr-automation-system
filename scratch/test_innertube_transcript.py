import json
import re
import urllib.request

def get_transcript_innertube(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    }

    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as resp:
        html = resp.read().decode('utf-8', errors='ignore')

    # Extrair INNERTUBE_API_KEY
    key_match = re.search(r'"INNERTUBE_API_KEY"\s*:\s*"([^"]+)"', html)
    if not key_match:
        print("INNERTUBE_API_KEY não encontrada")
        return None
    api_key = key_match.group(1)

    # Extrair ytInitialPlayerResponse
    player_match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});(?:var\s+|</script>)', html)
    if not player_match:
        print("ytInitialPlayerResponse não encontrado")
        return None

    player_data = json.loads(player_match.group(1))
    
    # Obter os dados de legendas/captions
    captions = player_data.get("captions", {}).get("playerCaptionsTracklistRenderer", {})
    caption_tracks = captions.get("captionTracks", [])

    print(f"API Key: {api_key[:10]}...")
    print(f"Trilhas de legenda: {len(caption_tracks)}")

    if not caption_tracks:
        print("Nenhuma legenda disponível para este vídeo.")
        return None

    # Tentar obter via timedtext direto sem fmt=json3 ou alterando parâmetros
    base_url = caption_tracks[0]["baseUrl"]
    print(f"Legenda encontrada: {caption_tracks[0].get('name', {}).get('simpleText')}")

    # Chamar InnerTube API: /youtubei/v1/get_transcript
    # Vamos extrair o params do getTranscriptEndpoint se disponível no html
    param_match = re.search(r'"getTranscriptEndpoint"\s*:\s*{\s*"params"\s*:\s*"([^"]+)"', html)
    
    if param_match:
        params_str = param_match.group(1)
        print(f"Params de transcrição encontrados: {params_str[:20]}...")
        
        innertube_url = f"https://www.youtube.com/youtubei/v1/get_transcript?key={api_key}"
        payload = {
            "context": {
                "client": {
                    "clientName": "WEB",
                    "clientVersion": "2.20240815.00.00",
                    "hl": "pt",
                    "gl": "BR"
                }
            },
            "params": params_str
        }
        
        post_data = json.dumps(payload).encode('utf-8')
        it_req = urllib.request.Request(
            innertube_url,
            data=post_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": headers["User-Agent"]
            }
        )
        
        try:
            with urllib.request.urlopen(it_req) as it_resp:
                res_json = json.loads(it_resp.read().decode('utf-8'))
                
                # Extrair segmentos da resposta do InnerTube
                actions = res_json.get("actions", [])
                lines = []
                for act in actions:
                    renderer = act.get("updateEngagementPanelAction", {}).get("content", {}).get("transcriptRenderer", {})
                    content = renderer.get("content", {}).get("transcriptSearchPanelRenderer", {}).get("body", {}).get("transcriptBodyRenderer", {})
                    c_list = content.get("cueGroups", [])
                    for cue in c_list:
                        cues = cue.get("transcriptCueGroupRenderer", {}).get("cues", [])
                        for c in cues:
                            runs = c.get("transcriptCueRenderer", {}).get("cue", {}).get("simpleText", "")
                            if runs:
                                lines.append(runs.strip())

                if lines:
                    clean_text = "\n".join(lines)
                    print(f"🎉 SUCESSO INNERTUBE! Total de frases: {len(lines)} | Palavras: {len(clean_text.split())}")
                    print("Amostra:")
                    print("\n".join(lines[:10]))
                    return clean_text
        except Exception as e:
            print(f"Erro no InnerTube get_transcript: {e}")

    return None

if __name__ == "__main__":
    get_transcript_innertube("Yx99q0tSxHM")
