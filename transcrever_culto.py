"""
Script de Transcrição Resiliente em Lote (Fase 2) com Pausa de Resfriamento da CPU.

Transcreve 1 a 1 os cultos locais em segundo plano, aplicando:
1. Limitação do FFmpeg para 1 thread (baixo uso de CPU ~25% para evitar travamento do notebook i5).
2. Pausa automática de resfriamento de 15 segundos entre cada culto.
3. Transcrição ultra-rápida via Groq API (Whisper Large V3).

Uso no Terminal:
    python transcrever_culto.py --all
"""

import sys
import os
import json
import time
import argparse
from pathlib import Path

# Suporte UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.infrastructure.groq_client import GroqWhisperClient

logger = get_logger("TranscreverCultoCLI")


def transcrever_single_audio(audio_path: Path, groq_client: GroqWhisperClient, cooldown_seconds: int = 15) -> bool:
    """Executa a transcrição de um único culto com baixo uso de CPU."""
    if not audio_path.exists():
        print(f"❌ Arquivo não encontrado: {audio_path}")
        return False

    trans_dir = Path("data/audio_podcasts/transcricoes_fase2")
    trans_dir.mkdir(parents=True, exist_ok=True)

    txt_file = trans_dir / f"{audio_path.stem}.txt"
    words_file = trans_dir / f"{audio_path.stem}.words.json"

    if txt_file.exists() and txt_file.stat().st_size > 100:
        print(f"⏩ [PULANDO] Transcrição já existe para {audio_path.name}")
        return True

    print(f"\n🎙️ [FASE 2] Transcrevendo culto 1 por 1: {audio_path.name} ({round(audio_path.stat().st_size / (1024*1024), 1)} MB)")
    
    try:
        result = groq_client.transcribe_audio(audio_path, job_id=f"job_cli_trans_{audio_path.stem}")
        print(f"✅ [SUCESSO] Transcrição concluída! ({result.get('words_count')} palavras)")
        print(f"   • Texto salvo em: {txt_file.name}")
        
        # Pausa de resfriamento para o notebook i5 não esquentar
        if cooldown_seconds > 0:
            print(f"❄️ Pausa de resfriamento da CPU ({cooldown_seconds}s para manter a máquina leve)...")
            time.sleep(cooldown_seconds)
            
        return True
    except Exception as e:
        print(f"❌ [ERRO] Falha ao transcrever {audio_path.name}: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Script de Transcrição Resiliente em Lote com Pausa")
    parser.add_argument("audio_path", nargs="?", help="Caminho de um áudio específico para transcrever")
    parser.add_argument("--all", action="store_true", help="Transcrever todos os cultos com pausa de resfriamento")
    parser.add_argument("--pause", type=int, default=15, help="Segundos de pausa entre cada culto (padrão: 15s)")

    args = parser.parse_args()

    groq_client = GroqWhisperClient()
    if not groq_client.client:
        print("❌ ERRO: GROQ_API_KEY não configurada no arquivo .env!")
        sys.exit(1)

    audio_dir = Path("data/audio_podcasts")

    if args.audio_path:
        target = Path(args.audio_path)
        if not target.exists():
            target = audio_dir / args.audio_path
        transcrever_single_audio(target, groq_client, cooldown_seconds=0)
    elif args.all:
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        print(f"🚀 Iniciando modo 1 por 1 com pausa de resfriamento para {len(audios)} cultos...")
        
        for idx, a in enumerate(audios, 1):
            print(f"\n--- [ Culto {idx} de {len(audios)} ] ---")
            transcrever_single_audio(a, groq_client, cooldown_seconds=args.pause)
    else:
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        if not audios:
            print("⚠️ Nenhum arquivo de áudio encontrado em 'data/audio_podcasts'.")
            sys.exit(0)
        
        print("🎯 Transcrevendo apenas o primeiro culto da fila...")
        transcrever_single_audio(audios[0], groq_client, cooldown_seconds=0)


if __name__ == "__main__":
    main()
