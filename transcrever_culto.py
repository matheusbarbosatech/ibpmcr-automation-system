"""
Script de Transcrição Exclusiva (Fase 2) - IBPM CR AUTOMATION SYSTEM.

Executa SOMENTE a transcrição do áudio local (sem rodar o Gemini ou renderizar vídeos).
Compacta o áudio para 16kHz mono via FFmpeg e transcreve via Groq Whisper Large V3 em segundos.

Uso no Terminal:
    python transcrever_culto.py                         # Transcreve o primeiro culto pendente
    python transcrever_culto.py --all                   # Transcreve todos os cultos pendentes
    python transcrever_culto.py "caminho/do/audio.mp3"  # Transcreve um áudio específico
"""

import sys
import os
import json
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


def transcrever_single_audio(audio_path: Path, groq_client: GroqWhisperClient) -> bool:
    """Executa a transcrição exclusiva de um único arquivo de áudio."""
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

    print(f"\n🎙️ [FASE 2] Transcrevendo áudio: {audio_path.name} ({round(audio_path.stat().st_size / (1024*1024), 1)} MB)")
    
    try:
        result = groq_client.transcribe_audio(audio_path, job_id=f"job_cli_trans_{audio_path.stem}")
        print(f"✅ [SUCESSO] Transcrição salva com {result.get('words_count')} palavras!")
        print(f"   • Texto: {txt_file}")
        print(f"   • Timestamps: {words_file}\n")
        return True
    except Exception as e:
        print(f"❌ [ERRO] Falha ao transcrever {audio_path.name}: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Script de Transcrição Exclusiva de Cultos (Fase 2)")
    parser.add_argument("audio_path", nargs="?", help="Caminho do arquivo MP3 local para transcrever")
    parser.add_argument("--all", action="store_true", help="Transcrever todos os cultos pendentes no acervo local")

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
        transcrever_single_audio(target, groq_client)
    elif args.all:
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        print(f"🚀 Processando transcrição em lote para {len(audios)} cultos locais...")
        for a in audios:
            transcrever_single_audio(a, groq_client)
    else:
        # Pega o primeiro culto pendente
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        if not audios:
            print("⚠️ Nenhum arquivo de áudio encontrado em 'data/audio_podcasts'.")
            sys.exit(0)
        
        print("🎯 Transcrevendo o primeiro culto do acervo local...")
        transcrever_single_audio(audios[0], groq_client)


if __name__ == "__main__":
    main()
