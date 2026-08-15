"""
Script de Varredura e Extração Direta de Legendas do YouTube - IBPM CR Automation System.

Varre o canal ou playlist da IBPM CR no YouTube via yt-dlp, verifica quais vídeos
possuem legendas/transcrições disponíveis (automáticas ou manuais) em português,
baixa instantaneamente em ~1-2 segundos por vídeo (SEM baixar vídeo nem áudio pesado)
e salva cada transcrição em Bloco de Notas (.txt) e (.json) na pasta oficial da Fase 2.

Economiza 100% do tempo e recursos de transcrição Whisper local para vídeos que já possuem legendas!
"""

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("VarreduraLegendasYouTube")


def parse_vtt_to_clean_text_and_json(vtt_content: str) -> tuple[str, List[Dict[str, Any]]]:
    """
    Converte o texto cru do formato VTT em um texto limpo (.txt) e em uma lista de segmentos sem repetições.
    """
    lines = vtt_content.splitlines()
    segments = []
    txt_lines = []
    
    timestamp_regex = re.compile(r'(\d{2}:\d{2}:\d{2}[\.,]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[\.,]\d{3})')
    
    current_start = None
    current_end = None
    current_text = []
    last_added_phrase = ""

    def seconds_from_vtt_time(ts: str) -> float:
        ts = ts.replace(',', '.')
        parts = ts.split(':')
        if len(parts) == 3:
            return float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
        return 0.0

    def clean_text_line(text: str) -> str:
        text = re.sub(r'<[^>]+>', '', text)  # remove tags HTML/VTT
        return text.strip()

    for line in lines:
        line_str = line.strip()
        if not line_str or line_str.startswith("WEBVTT") or line_str.startswith("Kind:") or line_str.startswith("Language:"):
            continue

        match = timestamp_regex.search(line_str)
        if match:
            if current_start and current_text:
                full_text = " ".join(current_text).strip()
                if full_text and full_text != last_added_phrase and not last_added_phrase.endswith(full_text):
                    clean_ts = current_start.split('.')[0]
                    txt_lines.append(f"[{clean_ts}] {full_text}")
                    segments.append({
                        "start": seconds_from_vtt_time(current_start),
                        "end": seconds_from_vtt_time(current_end),
                        "text": full_text
                    })
                    last_added_phrase = full_text
            current_start = match.group(1)
            current_end = match.group(2)
            current_text = []
        else:
            cleaned = clean_text_line(line_str)
            if cleaned and cleaned not in current_text:
                current_text.append(cleaned)

    if current_start and current_text:
        full_text = " ".join(current_text).strip()
        if full_text and full_text != last_added_phrase:
            clean_ts = current_start.split('.')[0]
            txt_lines.append(f"[{clean_ts}] {full_text}")
            segments.append({
                "start": seconds_from_vtt_time(current_start),
                "end": seconds_from_vtt_time(current_end),
                "text": full_text
            })

    formatted_txt = "\n".join(txt_lines)
    return formatted_txt, segments


def extrair_legendas_do_canal(url_canal_ou_playlist: str, output_dir: Path, max_videos: int = 440) -> Dict[str, Any]:
    """
    Varre o canal/playlist, identifica vídeos com legendas e salva em .txt e .json na pasta da Fase 2.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    temp_vtt_dir = output_dir / "_temp_vtt"
    temp_vtt_dir.mkdir(parents=True, exist_ok=True)

    logger.info("🔍 Iniciando varredura do YouTube para checar transcrições/legendas...", url=url_canal_ou_playlist)

    # 1. Lista os vídeos da playlist/canal via yt-dlp sem baixar vídeo nem áudio
    cmd_flat = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-end", str(max_videos),
        url_canal_ou_playlist
    ]

    try:
        res = subprocess.run(cmd_flat, capture_output=True, text=True, check=True)
        video_entries = [json.loads(line) for line in res.stdout.splitlines() if line.strip()]
        logger.info(f"📋 {len(video_entries)} vídeos encontrados no canal/playlist!")
    except Exception as e:
        logger.error("Falha ao listar vídeos do YouTube", error=str(e))
        return {"total_videos": 0, "legendas_baixadas": 0}

    legendas_baixadas = 0
    sem_legenda = 0

    for idx, video in enumerate(video_entries, start=1):
        v_id = video.get("id")
        v_title = video.get("title", f"culto_{idx}")
        v_url = f"https://www.youtube.com/watch?v={v_id}"

        # Nome limpo padronizado
        title_slug = re.sub(r'[^a-zA-Z0-9]', '_', v_title.lower())
        title_slug = re.sub(r'_+', '_', title_slug).strip('_')
        prefix = f"{idx:03d}_{title_slug[:50]}"
        
        txt_file = output_dir / f"{prefix}.txt"
        json_file = output_dir / f"{prefix}.json"

        if txt_file.exists() and json_file.exists():
            logger.info(f"⏩ Transcrição [{idx}/{len(video_entries)}] já existe localmente: {txt_file.name}")
            legendas_baixadas += 1
            continue

        # Baixa apenas o arquivo de legenda .vtt em 1 segundo
        vtt_template = str(temp_vtt_dir / f"{prefix}.%(ext)s")
        cmd_sub = [
            "yt-dlp",
            "--write-auto-sub",
            "--write-sub",
            "--sub-lang", "pt,pt-BR,pt-pt",
            "--sub-format", "vtt",
            "--skip-download",
            "-o", vtt_template,
            v_url
        ]

        try:
            sub_res = subprocess.run(cmd_sub, capture_output=True, text=True)
            
            # Procura o arquivo .vtt gerado no diretório temporário
            vtt_files = list(temp_vtt_dir.glob(f"{prefix}*.vtt"))
            if not vtt_files:
                logger.warning(f"⚠️ [{idx}/{len(video_entries)}] Sem legenda disponível no YouTube para: '{v_title}'")
                sem_legenda += 1
                continue

            # Lê e converte o VTT para o formato de Bloco de Notas limpo
            vtt_path = vtt_files[0]
            with open(vtt_path, "r", encoding="utf-8", errors="ignore") as f:
                vtt_text = f.read()

            clean_txt, segments = parse_vtt_to_clean_text_and_json(vtt_text)

            if not clean_txt:
                logger.warning(f"⚠️ [{idx}/{len(video_entries)}] Legenda em branco para: '{v_title}'")
                sem_legenda += 1
                vtt_path.unlink(missing_ok=True)
                continue

            header = f"""================================================================================
TRANSCRIÇÃO EXTRAÍDA DIRETAMENTE DO YOUTUBE (IBPM CR)
VÍDEO #{idx}: {v_title}
URL: {v_url}
================================================================================\n\n"""

            with open(txt_file, "w", encoding="utf-8") as f:
                f.write(header + clean_txt)

            with open(json_file, "w", encoding="utf-8") as f:
                json.dump({
                    "video_index": idx,
                    "video_id": v_id,
                    "title": v_title,
                    "url": v_url,
                    "segments": segments
                }, f, ensure_ascii=False, indent=2)

            # Limpa temporário
            vtt_path.unlink(missing_ok=True)
            legendas_baixadas += 1
            logger.info(f"✅ [{idx}/{len(video_entries)}] TRANSCRIÇÃO COPIADA COM SUCESSO! -> {txt_file.name}")

        except Exception as err:
            logger.error(f"Erro ao processar legenda de {v_title}", error=str(err))
            sem_legenda += 1

    # Remove diretório temporário VTT
    try:
        for f in temp_vtt_dir.glob("*"):
            f.unlink()
        temp_vtt_dir.rmdir()
    except Exception:
        pass

    print("\n" + "=" * 60)
    print(" VARREDURA E EXTRAÇÃO DE LEGENDAS DO YOUTUBE CONCLUÍDA!")
    print(f" * Total de vídeos analisados: {len(video_entries)}")
    print(f" * Transcrições aproveitadas do YouTube: {legendas_baixadas}")
    print(f" * Vídeos que precisarão de transcrição Whisper local: {sem_legenda}")
    print(f" * Pasta de destino: '{output_dir}'")
    print("=" * 60 + "\n")

    return {
        "total_videos": len(video_entries),
        "legendas_baixadas": legendas_baixadas,
        "sem_legenda": sem_legenda,
        "output_dir": str(output_dir)
    }


def main():
    parser = argparse.ArgumentParser(description="Varredura de legendas do YouTube para canal da IBPM CR")
    parser.add_argument("--url", default="https://www.youtube.com/playlist?list=UUHhLxWRcCB-xKo0ifOQ8MVQ", help="URL do canal ou playlist da IBPM CR")
    parser.add_argument("--out", default="data/audio_podcasts/transcricoes_fase2", help="Pasta oficial de destino das transcrições")
    parser.add_argument("--max", type=int, default=440, help="Quantidade máxima de vídeos a varrer")

    args = parser.parse_args()
    out_dir = Path(args.out)

    extrair_legendas_do_canal(args.url, out_dir, max_videos=args.max)


if __name__ == "__main__":
    main()
