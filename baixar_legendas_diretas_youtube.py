import sys
import os
import re
import json
import time
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
DEST_DIR = BASE_DIR / "data" / "1.TRANSCRICOES"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Accept-Language': 'pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7',
}

def extrair_legenda_direta(video_id):
    url = f"https://www.youtube.com/watch?v={video_id}"
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        html = urllib.request.urlopen(req, timeout=10).read().decode('utf-8')
        
        pos = html.find('captionTracks')
        if pos == -1:
            return None, "sem_caption_tracks"

        start = html.find('[', pos)
        end = html.find(']', start) + 1
        tracks = json.loads(html[start:end])

        if not tracks:
            return None, "sem_tracks"

        base_url = tracks[0]['baseUrl']
        req_xml = urllib.request.Request(base_url, headers=HEADERS)
        xml_data = urllib.request.urlopen(req_xml, timeout=10).read().decode('utf-8')

        root = ET.fromstring(xml_data)
        lines = []
        for elem in root.findall('text'):
            start_sec = float(elem.attrib.get('start', '0'))
            secs = int(start_sec)
            hrs = secs // 3600
            mins = (secs % 3600) // 60
            s = secs % 60
            txt = elem.text or ''
            txt = txt.replace('\n', ' ').replace('&quot;', '"').replace('&amp;', '&').replace('&#39;', "'")
            txt = re.sub(r'<.*?>', '', txt).strip()
            if txt:
                lines.append(f"[{hrs:02d}:{mins:02d}:{s:02d}] {txt}")

        if lines:
            return "\n".join(lines), "youtube_direct_html"

    except Exception as ex:
        return None, str(ex)

    return None, "erro_desconhecido"

def main():
    print("=" * 80)
    print("🚀 EXTRAÇÃO DIRETA DE LEGENDAS YOUTUBE (HTML/XML TIMEDTEXT)")
    print("=" * 80)

    txt_files = sorted(list(DEST_DIR.glob('*.txt')))
    print(f"Total de arquivos na pasta data/1.TRANSCRICOES: {len(txt_files)}")

    baixados = 0
    ja_tinham = 0
    sem_legenda = 0

    for idx, f in enumerate(txt_files, 1):
        content = f.read_text(encoding='utf-8', errors='ignore')
        
        # Se ja tiver transcrição real completa
        if 'PENDENTE DE TRANSCRIÇÃO' not in content and len(content) > 500:
            ja_tinham += 1
            continue

        m = re.search(r'ID:\s*([a-zA-Z0-9_-]{11})', content)
        if not m:
            m2 = re.search(r'_\d{4}-\d{2}-\d{2}_([a-zA-Z0-9_-]{11})_', f.name)
            vid = m2.group(1) if m2 else None
        else:
            vid = m.group(1)

        if not vid: continue

        lines_text, status = extrair_legenda_direta(vid)

        if lines_text:
            header = f"="*80 + f"\nTRANSCRIÇÃO OFICIAL YOUTUBE (DIRECT_HTML) | ARQUIVO: {f.name}\nURL: https://www.youtube.com/watch?v={vid}\n" + "="*80 + "\n\n"
            f.write_text(header + lines_text, encoding='utf-8')
            baixados += 1
            print(f"[{idx:03d}/{len(txt_files)}] ✅ TRANSCRIÇÃO BAIXADA! -> {f.name}")
        else:
            sem_legenda += 1
            if 'G4gzehT0olc' in vid:
                print(f"[{idx:03d}/{len(txt_files)}] ❌ G4gzehT0olc status: {status}")

        time.sleep(0.3)

    print("\n" + "🎉" * 20)
    print(f"• Arquivos com transcrição oficial baixada: {ja_tinham + baixados}")
    print(f"• Novos arquivos atualizados nesta rodada: {baixados}")
    print(f"• Arquivos mantidos pendentes para GPU: {sem_legenda}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
