#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script para baixar TODOS os 457 áudios do canal IBPM em ordem cronológica (001 = mais antigo, 457 = mais recente),
com numeração no nome do arquivo, máxima qualidade de áudio e menor tamanho de arquivo (Opus/WebM/M4A nativos do YouTube).

Uso:
  python scripts/audio/baixar_todos_audios_cronologico.py
"""

import sys
import json
import os
import re
import subprocess
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_JSON = BASE_DIR / "data" / "fase1_mapeamento" / "canal_ibpm_todos_videos.json"
PASTA_AUDIOS = BASE_DIR / "dataset_transcricoes" / "audios"
COOKIES_FILE = BASE_DIR / "cookies.txt"

def sanitizar_nome(texto: str) -> str:
    """Sanitiza o título para uso seguro no sistema de arquivos."""
    texto_limpo = re.sub(r'[\\/*?:"<>|]', '', texto)
    texto_limpo = re.sub(r'[\s_]+', '_', texto_limpo).strip('_')
    return texto_limpo[:80]

def garantir_dependencias():
    try:
        import yt_dlp
    except ImportError:
        print("📦 Instalando biblioteca yt-dlp para download de alta velocidade...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "yt-dlp"])

def main():
    garantir_dependencias()
    import yt_dlp

    print("==========================================================================")
    print("🚀 DOWNLOAD CRONOLÓGICO DOS ÁUDIOS DO CANAL IBPM")
    print("   • Ordem: Do mais antigo (001) ao mais recente (457)")
    print("   • Qualidade: Máxima qualidade original de áudio (Opus/WebM/M4A sem perdas)")
    print("   • Tamanho: Formato mais leve e eficiente diretamente do YouTube")
    print("==========================================================================\n")

    if not DATA_JSON.exists():
        print(f"❌ Erro: Arquivo de catálogo {DATA_JSON} não encontrado!")
        sys.exit(1)

    PASTA_AUDIOS.mkdir(parents=True, exist_ok=True)

    with open(DATA_JSON, "r", encoding="utf-8") as f:
        videos_raw = json.load(f)

    # Inverter lista para que o mais antigo fique no índice 0
    # No catálogo canal_ibpm_todos_videos.json:
    #   índice 0 = mais recente (2026)
    #   índice -1 = mais antigo (2022)
    videos_cronologicos = list(reversed(videos_raw))
    total_videos = len(videos_cronologicos)

    print(f"📊 Total de vídeos no catálogo: {total_videos}")
    print(f"📂 Pasta de destino local: {PASTA_AUDIOS.resolve()}\n")

    # Mapear arquivos locais já baixados para evitar re-download
    arquivos_locais = list(PASTA_AUDIOS.glob("*.*"))
    ids_baixados = set()
    indices_baixados = set()

    for arq in arquivos_locais:
        match_idx = re.match(r'^(\d{3})_', arq.name)
        if match_idx:
            indices_baixados.add(int(match_idx.group(1)))
        
        match_id = re.search(r'([a-zA-Z0-9_-]{11})', arq.name)
        if match_id:
            ids_baixados.add(match_id.group(1))

    print(f"🔍 Encontrados {len(arquivos_locais)} arquivos já existentes na pasta local.")

    # Lista de downloads pendentes
    pendentes = []
    for idx, vid in enumerate(videos_cronologicos, start=1):
        vid_id = vid['id']
        titulo = vid.get('title', '')
        titulo_clean = sanitizar_nome(titulo)
        prefixo = f"{idx:03d}"
        nome_base = f"{prefixo}_{vid_id}_{titulo_clean}".rstrip('_')

        # Se o ID ou o índice já existem localmente, pula
        if idx in indices_baixados or vid_id in ids_baixados:
            continue

        pendentes.append((idx, vid_id, titulo, nome_base))

    print(f"🎯 Pendentes para download: {len(pendentes)} de {total_videos}\n")

    if not pendentes:
        print("🎉 Todos os 457 áudios já foram baixados e estão na pasta!")
        return

    # Opções do yt-dlp otimizadas para qualidade e velocidade
    ydl_opts_base = {
        'format': 'bestaudio/best',
        'ignoreerrors': True,
        'retries': 10,
        'fragment_retries': 10,
        'concurrent_fragment_downloads': 5,
        'quiet': False,
        'no_warnings': True,
        'extractor_args': {
            'youtube': {
                'player_client': ['android', 'web']
            }
        }
    }

    if COOKIES_FILE.exists():
        print(f"🍪 Usando arquivo de cookies: {COOKIES_FILE}")
        ydl_opts_base['cookiefile'] = str(COOKIES_FILE)

    sucessos = 0
    erros = 0

    for i, (idx, vid_id, titulo, nome_base) in enumerate(pendentes, start=1):
        print(f"[{i}/{len(pendentes)}] 📥 [{idx:03d}/{total_videos}] Baixando: {titulo} (ID: {vid_id})...")
        
        caminho_saida = PASTA_AUDIOS / f"{nome_base}.%(ext)s"
        ydl_opts = dict(ydl_opts_base)
        ydl_opts['outtmpl'] = str(caminho_saida)

        url = f"https://www.youtube.com/watch?v={vid_id}"

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                res = ydl.download([url])
                if res == 0:
                    sucessos += 1
                else:
                    erros += 1
        except Exception as e:
            print(f"   ❌ Erro ao baixar vídeo {vid_id}: {e}")
            erros += 1

    print("\n==========================================================================")
    print("🎉 PROCESSAMENTO CONCLUÍDO!")
    print(f"   • Áudios baixados nesta sessão: {sucessos}")
    print(f"   • Erros/Falhas:                 {erros}")
    print(f"   • Total de arquivos na pasta:   {len(list(PASTA_AUDIOS.glob('*.*')))}")
    print("==========================================================================")

if __name__ == "__main__":
    main()
