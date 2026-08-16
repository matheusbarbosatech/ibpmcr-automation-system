"""
executar_fase1_mapeamento_canal.py
==================================
Reformulação Perfeita da Fase 1 - IBPM CR:
1. Mapeia e ordena todos os 456 vídeos CRONOLOGICAMENTE (2022 -> 2026).
2. Baixa as legendas do YouTube via yt-dlp usando Node.js JS runtime (--js-runtimes node).
3. Salva em data/1.TRANSCRICOES/ mantendo exatamente 456 arquivos.
"""

import sys
import os
import re
import json
import time
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from youtube_transcript_api import YouTubeTranscriptApi

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

def parse_date_from_title(title):
    if '07/13' in title: return '2023-07-13'
    m = re.search(r'(\d{1,2})[\/\\\.-](\d{1,2})[\/\\\.-](\d{2,4})', title)
    if m:
        day = int(m.group(1))
        month = int(m.group(2))
        year_str = m.group(3)
        year = 2000 + int(year_str) if len(year_str) == 2 else int(year_str)
        if 2020 <= year <= 2030 and 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
            
    m2 = re.search(r'(\d{1,2})[\/\\\.-](\d{1,2})', title)
    if m2:
        day = int(m2.group(1))
        month = int(m2.group(2))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"2023-{month:02d}-{day:02d}"
            
    return '9999-99-99'

def obter_transcricao_youtube(video_id):
    # 1. Tentar via yt-dlp com --js-runtimes node
    try:
        sub_file = BASE_DIR / f"temp_sub_{video_id}"
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--write-sub',
            '--sub-lang', 'pt,pt-orig,pt-BR',
            '--sub-format', 'vtt',
            '--js-runtimes', 'node',
            '--no-check-certificates',
            '-o', str(sub_file),
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        if COOKIES_FILE.exists():
            cmd.extend(['--cookies', str(COOKIES_FILE)])
        
        subprocess.run(cmd, capture_output=True, text=True, timeout=25)
        vtt_files = list(BASE_DIR.glob(f"temp_sub_{video_id}*.vtt"))
        if vtt_files:
            vtt_p = vtt_files[0]
            vtt_content = vtt_p.read_text(encoding='utf-8', errors='ignore')
            vtt_p.unlink(missing_ok=True)
            
            lines = []
            seen = set()
            for m in re.finditer(r'(\d{2}:\d{2}:\d{2})\.\d{3}\s+-->\s+\d{2}:\d{2}:\d{2}\.\d{3}\n(.*?)(?=\n\n|\n\d{2}:|$)', vtt_content, re.DOTALL):
                ts = m.group(1)
                text = re.sub(r'<.*?>', '', m.group(2)).strip().replace('\n', ' ')
                if text and text not in seen:
                    seen.add(text)
                    lines.append(f"[{ts}] {text}")
            if lines:
                return "\n".join(lines), "yt_dlp_vtt"
    except Exception:
        pass

    # 2. Fallback YouTubeTranscriptApi
    try:
        ytt_api = YouTubeTranscriptApi()
        ts_list = ytt_api.fetch(video_id, languages=['pt', 'pt-BR', 'pt-orig'])
        lines = []
        for snippet in ts_list:
            sec = getattr(snippet, 'start', 0.0)
            text = getattr(snippet, 'text', '').strip().replace('\n', ' ')
            if text:
                lines.append(f"[{format_timestamp(sec)}] {text}")
        if lines:
            return "\n".join(lines), "youtube_api"
    except Exception:
        pass

    return None, None

def carregar_e_ordenar_videos():
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        item['parsed_date'] = parse_date_from_title(item.get('title', ''))
    data.sort(key=lambda x: (x['parsed_date'], x.get('title', '')))
    return data

def main():
    print("=" * 70)
    print("🚀 FASE 1: DOWLOAD COMPLETO DE TRANSCRIÇÕES DO YOUTUBE (001 a 456)")
    print("=" * 70)

    videos = carregar_e_ordenar_videos()
    total_videos = len(videos)

    com_trans = 0
    sem_trans = 0

    for idx, item in enumerate(videos, 1):
        vid = item.get('id')
        raw_title = item.get('title', 'culto')
        c_title = clean_title(raw_title)
        parsed_date = item.get('parsed_date', '2023-01-01')

        filename = f"{idx:03d}_{parsed_date}_{vid}_{c_title}.txt"
        target_file = DEST_DIR / filename

        # Se ja tiver transcricao real baixada (> 500 bytes e sem marca de PENDENTE)
        if target_file.exists():
            curr_text = target_file.read_text(encoding='utf-8', errors='ignore')
            if 'PENDENTE DE TRANSCRIÇÃO' not in curr_text and len(curr_text) > 500:
                com_trans += 1
                continue

        text, source = obter_transcricao_youtube(vid)

        if text and len(text.strip()) > 100:
            header = f"="*80 + f"\nTRANSCRIÇÃO OFICIAL YOUTUBE ({source.upper()}) | VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\nDATA: {parsed_date}\n" + "="*80 + "\n\n"
            target_file.write_text(header + text, encoding='utf-8')
            com_trans += 1
            print(f"[{idx:03d}/{total_videos}] ✅ Transcrição baixada ({source}) -> {filename}")
        else:
            header = f"="*80 + f"\n[PENDENTE DE TRANSCRIÇÃO VIA GPU/WHISPER] VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\nDATA: {parsed_date}\nID: {vid}\n" + "="*80 + "\n\n"
            header += f"[00:00:00] Arquivo reservado para transcrição automática via GPU Whisper.\n"
            target_file.write_text(header, encoding='utf-8')
            sem_trans += 1

        time.sleep(0.5)

    print("\n" + "🎉" * 20)
    print("FASE 1 CONCLUÍDA COM SUCESSO!")
    print(f"• Total de arquivos em data/1.TRANSCRICOES: {len(list(DEST_DIR.glob('*.txt')))}")
    print(f"• Transcrições baixadas do YouTube: {com_trans}")
    print(f"• Arquivos pendentes (para GPU Whisper): {sem_trans}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
