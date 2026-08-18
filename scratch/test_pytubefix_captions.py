import requests
import xml.etree.ElementTree as ET
from pytubefix import YouTube

def test_pytubefix(video_id: str):
    url = f"https://www.youtube.com/watch?v={video_id}"
    yt = YouTube(url, client='WEB')
    print(f"Título: {yt.title}")
    
    captions = yt.captions
    print(f"Captações encontradas ({len(captions)}):")
    for caption in captions:
        print(f" -> Code: {caption.code} | Name: {caption.name} | URL: {caption.url[:80]}...")
        
        # Baixar a URL do XML com User-Agent de navegador real
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": "https://www.youtube.com/"
        }
        
        # Obter XML em formato ttml/vtt ou xml
        xml_url = caption.url
        res = requests.get(xml_url, headers=headers)
        print(f"Status do Download: {res.status_code}")
        
        if res.status_code == 200:
            xml_text = res.text
            # Parsear XML do YouTube (format <text start="12.3" dur="4.5">Texto</text>)
            root = ET.fromstring(xml_text)
            lines = []
            for child in root.findall(".//text"):
                if child.text:
                    lines.append(child.text.strip())
            
            clean_text = "\n".join(lines)
            print(f"🎉 SUCESSO TOTAL E ABSOLUTO! Total de frases: {len(lines)} | Palavras: {len(clean_text.split())}")
            print("Amostra:")
            print("\n".join(lines[:10]))
            return clean_text
        else:
            print("Erro no download:", res.status_code, res.text[:200])

if __name__ == "__main__":
    test_pytubefix("JZqi2LW0Jmw")
