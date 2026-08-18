import http.cookiejar
import requests
from youtube_transcript_api import YouTubeTranscriptApi

def test_ytt():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
        "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7"
    })
    
    cj = http.cookiejar.MozillaCookieJar('cookies.txt')
    try:
        cj.load(ignore_discard=True, ignore_expires=True)
        session.cookies.update(cj)
        print("Cookies adicionados à sessão.")
    except Exception as e:
        print(f"Sem cookies: {e}")

    try:
        ytt = YouTubeTranscriptApi(http_client=session)
        transcript = ytt.fetch('Yx99q0tSxHM', languages=['pt', 'pt-BR'])
        print(f"SUCESSO YTT! Segmentos: {len(transcript)}")
        print("Amostra:", transcript[0])
    except Exception as e:
        print(f"Erro no YTT com sessão: {type(e).__name__} - {e}")

if __name__ == "__main__":
    test_ytt()
