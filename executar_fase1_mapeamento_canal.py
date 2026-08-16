"""
executar_fase1_mapeamento_canal.py
==================================
Reformulação Perfeita da Fase 1 - IBPM CR:
1. Limpa e recria data/1.TRANSCRICOES/
2. Mapeia e ordena todos os 456 vídeos CRONOLOGICAMENTE (2022 -> 2026) com base nas datas reais extraídas do título/upload.
   - 001: Mais antigo (2022)
   - 456: Mais recente (15/08/26 - 5° DIA DE FESTIVIDADE - JUVENTUDE)
3. Baixa e salva TODAS as transcrições disponíveis no YouTube usando a API corrigida (api.fetch com idiomas pt/pt-BR).
4. Se o vídeo não tiver transcrição no YouTube, salva o arquivo pré-formatado (PENDENTE GPU WHISPER) mantendo a sequência perfeita de 001 a 456.
"""

import sys
import os
import re
import json
import time
import shutil
import subprocess
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

from youtube_transcript_api import YouTubeTranscriptApi

BASE_DIR = Path(__file__).resolve().parent
DEST_DIR = BASE_DIR / "data" / "1.TRANSCRICOES"

# Recriar diretório limpo
if DEST_DIR.exists():
    shutil.rmtree(DEST_DIR)
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
    if '07/13' in title:
        return '2023-07-13'
    # Match DD/MM/YYYY ou DD/MM/YY com barras, contra-barras ou pontos
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

def obter_transcricao_youtube(video_id, ytt_api):
    try:
        ts_list = ytt_api.fetch(video_id, languages=['pt', 'pt-BR'])
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

    # Fallback yt-dlp
    try:
        sub_file = BASE_DIR / f"temp_sub_{video_id}"
        cmd = [
            'yt-dlp',
            '--skip-download',
            '--write-auto-sub',
            '--sub-lang', 'pt',
            '--sub-format', 'vtt',
            '--no-check-certificates',
            '-o', str(sub_file),
            f'https://www.youtube.com/watch?v={video_id}'
        ]
        if COOKIES_FILE.exists():
            cmd.extend(['--cookies', str(COOKIES_FILE)])
        
        subprocess.run(cmd, capture_output=True, text=True, timeout=20)
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

    return None, None

def carregar_e_ordenar_videos():
    if not CACHE_FILE.exists():
        print(f"Erro: {CACHE_FILE} não encontrado.")
        sys.exit(1)
    
    with open(CACHE_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)

    for item in data:
        item['parsed_date'] = parse_date_from_title(item.get('title', ''))

    # Ordenar cronologicamente do mais antigo ao mais recente
    data.sort(key=lambda x: (x['parsed_date'], x.get('title', '')))
    return data

def processar_item(args_tuple):
    idx, item, total_videos = args_tuple
    vid = item.get('id')
    raw_title = item.get('title', 'culto')
    c_title = clean_title(raw_title)
    parsed_date = item.get('parsed_date', '2023-01-01')

    filename = f"{idx:03d}_{parsed_date}_{vid}_{c_title}.txt"
    target_file = DEST_DIR / filename

    ytt_api = YouTubeTranscriptApi()
    text, source = obter_transcricao_youtube(vid, ytt_api)

    if text and len(text.strip()) > 100:
        header = f"="*80 + f"\nTRANSCRIÇÃO OFICIAL YOUTUBE ({source.upper()}) | VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\nDATA: {parsed_date}\n" + "="*80 + "\n\n"
        target_file.write_text(header + text, encoding='utf-8')
        return idx, filename, True, source
    else:
        header = f"="*80 + f"\n[PENDENTE DE TRANSCRIÇÃO VIA GPU/WHISPER] VÍDEO #{idx:03d}: {raw_title}\nURL: https://www.youtube.com/watch?v={vid}\nDATA: {parsed_date}\nID: {vid}\n" + "="*80 + "\n\n"
        header += f"[00:00:00] Arquivo reservado para transcrição automática via GPU Whisper.\n"
        target_file.write_text(header, encoding='utf-8')
        return idx, filename, False, "pendente"

def main():
    print("=" * 70)
    print("🚀 FASE 1 REFORMULADA: ORDENAÇÃO CRONOLÓGICA (001 a 456) & TRANSCRIÇÕES")
    print("=" * 70)

    videos = carregar_e_ordenar_videos()
    total_videos = len(videos)

    print(f"\n📂 Total de vídeos no canal: {total_videos}")
    print(f"🗓️  Primeiro Vídeo (#001): [{videos[0]['parsed_date']}] {videos[0]['title']}")
    print(f"🗓️  Último Vídeo (#456):   [{videos[-1]['parsed_date']}] {videos[-1]['title']}")
    print(f"📁 Pasta Destino: {DEST_DIR}\n")

    tasks = [(idx, item, total_videos) for idx, item in enumerate(videos, 1)]

    com_transcricao = 0
    sem_transcricao = 0

    with ThreadPoolExecutor(max_workers=12) as executor:
        futures = [executor.submit(processar_item, t) for t in tasks]
        for f in as_completed(futures):
            idx, filename, ok, source = f.result()
            if ok:
                com_transcricao += 1
            else:
                sem_transcricao += 1
            if idx % 50 == 0 or idx == total_videos:
                print(f"  Progresso: [{idx:03d}/{total_videos}] -> {filename} ({source})")

    all_txt = list(DEST_DIR.glob('*.txt'))
    print("\n" + "🎉" * 20)
    print("FASE 1 REFORMULADA CONCLUÍDA COM SUCESSO!")
    print(f"• Total de arquivos criados em data/1.TRANSCRICOES: {len(all_txt)}")
    print(f"• Transcrições baixadas do YouTube: {com_transcricao}")
    print(f"• Arquivos pendentes (para GPU Whisper): {sem_transcricao}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
