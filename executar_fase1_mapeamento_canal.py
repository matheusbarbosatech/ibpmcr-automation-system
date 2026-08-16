"""
executar_fase1_mapeamento_canal.py (Versão Multi-Threaded Ultrarrápida)
======================================================================
1. Lê o acervo de 456 vídeos do canal IBPM CR (abas /videos e /streams).
2. Ordena do mais antigo (001) ao mais recente (456).
3. Processa em paralelo (ThreadPoolExecutor com 8 workers) o download de legendas.
4. Salva 100% dos 456 arquivos .txt em: data/1.TRANSCRICOES/
"""

import sys
import os
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

try:
    from youtube_transcript_api import YouTubeTranscriptApi
    HAS_TRANSCRIPT_API = True
except ImportError:
    HAS_TRANSCRIPT_API = False

BASE_DIR = Path(__file__).resolve().parent
DEST_DIR = BASE_DIR / "data" / "1.TRANSCRICOES"
DEST_DIR.mkdir(parents=True, exist_ok=True)

CACHE_FILE = BASE_DIR / "data" / "canal_ibpm_todos_videos.json"
COOKIES_FILE = BASE_DIR / "data" / "youtube_cookies.txt"

def clean_title(title):
    title = re.sub(r'[^\w\s-]', '', title, flags=re.UNICODE)
    title = re.sub(r'\s+', '_', title).strip('_').lower()
    return title[:60] if title else "culto_ibpm"

def format_timestamp(seconds):
    hrs = int(seconds // 3600)
    mins = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"

def obter_transcricao_youtube(video_id):
    if HAS_TRANSCRIPT_API:
        try:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['pt', 'pt-BR'])
            lines = []
            for item in transcript_list:
                start_sec = item.get('start', 0.0)
                ts_str = format_timestamp(start_sec)
                text = item.get('text', '').strip().replace('\n', ' ')
                if text:
                    lines.append(f"[{ts_str}] {text}")
            if lines:
                return "\n".join(lines), "youtube_transcript_api"
        except Exception:
            pass
    return None, None

def processar_item(args_tuple):
    idx, item, total_videos = args_tuple
    vid = item.get('id')
    raw_title = item.get('title', 'culto')
    c_title = clean_title(raw_title)
    upload_date = item.get('upload_date') or '2023-01-01'

    if len(upload_date) == 8:
        formatted_date = f"{upload_date[:4]}-{upload_date[4:6]}-{upload_date[6:]}"
    else:
        formatted_date = upload_date

    filename = f"{idx:03d}_{formatted_date}_{vid}_{c_title}.txt"
    target_file = DEST_DIR / filename

    if target_file.exists() and target_file.stat().st_size > 500:
        return idx, filename, True, "existente"

    text, source = obter_transcricao_youtube(vid)

    if text and len(text.strip()) > 100:
        header = f"="*80 + f"\nTRANSCRIÇÃO YOUTUBE ({source.upper()}) | VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\n" + "="*80 + "\n\n"
        target_file.write_text(header + text, encoding='utf-8')
        return idx, filename, True, source
    else:
        header = f"="*80 + f"\n[PENDENTE DE TRANSCRIÇÃO VIA GPU/WHISPER] VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\nDATA: {formatted_date}\nID: {vid}\n" + "="*80 + "\n\n"
        header += f"[00:00:00] Arquivo reservado para transcrição automática via GPU Whisper.\n"
        target_file.write_text(header, encoding='utf-8')
        return idx, filename, False, "pendente"

def carregar_lista_videos():
    if not CACHE_FILE.exists():
        print(f"Erro: Arquivo {CACHE_FILE} não encontrado.")
        sys.exit(1)
    
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    def get_sort_key(item):
        date = item.get('upload_date') or ''
        ts = item.get('timestamp') or 0
        return (date, ts, item.get('id', ''))

    data.sort(key=get_sort_key)
    return data

def main():
    print("=" * 70)
    print("🚀 REFORMULAÇÃO FASE 1: MAPEAR CANAL IBPM CR & POPULAR data/1.TRANSCRICOES")
    print("=" * 70)

    videos = carregar_lista_videos()
    total_videos = len(videos)
    print(f"\n📂 Total de vídeos mapeados no canal: {total_videos}")
    print(f"📁 Pasta de Destino: {DEST_DIR}\n")

    tasks = [(idx, item, total_videos) for idx, item in enumerate(videos, 1)]

    com_transcricao = 0
    sem_transcricao = 0

    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(processar_item, t) for t in tasks]
        for f in as_completed(futures):
            idx, filename, ok, source = f.result()
            if ok:
                com_transcricao += 1
            else:
                sem_transcricao += 1
            if idx % 50 == 0 or idx == total_videos:
                print(f"  Progresso: [{idx:03d}/{total_videos}] {filename} ({source})")

    all_txt = list(DEST_DIR.glob('*.txt'))
    print("\n" + "🎉" * 20)
    print("FASE 1 CONCLUÍDA COM SUCESSO!")
    print(f"• Total de arquivos em data/1.TRANSCRICOES: {len(all_txt)}")
    print(f"• Transcrições obtidas do YouTube: {com_transcricao}")
    print(f"• Arquivos marcados como pendentes (para GPU Whisper): {sem_transcricao}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
