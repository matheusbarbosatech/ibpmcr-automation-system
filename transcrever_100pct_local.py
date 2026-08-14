"""
Script de Transcrição 100% Offline e Local (Fase 2) - IBPM CR AUTOMATION SYSTEM.

NÃO USA GROQ, NÃO USA API E NÃO PRECISA DE INTERNET.
Utiliza a engine 'faster-whisper' quantizada em 'int8' na CPU para rodar em notebooks i5 leves
com consumo de RAM baixíssimo (~450 MB) e modelo 'base' ou 'tiny'.

Uso no Terminal:
    python transcrever_100pct_local.py                         # Transcreve o primeiro culto pendente
    python transcrever_100pct_local.py --all                   # Transcreve todos os cultos com pausa
    python transcrever_100pct_local.py --model tiny            # Usa modelo ultra-leve 'tiny'
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

from faster_whisper import WhisperModel
from src.core.logger import get_logger

logger = get_logger("LocalWhisperTranscriber")


def transcrever_audio_local(audio_path: Path, model: WhisperModel, cooldown_seconds: int = 10) -> bool:
    """Executa a transcrição 100% offline de um único arquivo de áudio."""
    if not audio_path.exists():
        print(f"❌ Arquivo não encontrado: {audio_path}")
        return False

    trans_dir = Path("data/audio_podcasts/transcricoes_fase2")
    trans_dir.mkdir(parents=True, exist_ok=True)

    txt_file = trans_dir / f"{audio_path.stem}.txt"
    words_file = trans_dir / f"{audio_path.stem}.words.json"

    if txt_file.exists() and txt_file.stat().st_size > 100:
        print(f"⏩ [PULANDO] Transcrição offline já existe para {audio_path.name}")
        return True

    print(f"\n🎙️ [100% LOCAL - SEM API] Transcrevendo culto: {audio_path.name} ({round(audio_path.stat().st_size / (1024*1024), 1)} MB)")
    print("   Processando via CTranslate2 CPU int8 em segundo plano...")

    try:
        start_t = time.time()
        segments, info = model.transcribe(
            str(audio_path),
            language="pt",
            beam_size=1,
            word_timestamps=True,
            vad_filter=True
        )

        full_text_list = []
        words_data = []

        for segment in segments:
            full_text_list.append(segment.text.strip())
            if hasattr(segment, "words") and segment.words:
                for w in segment.words:
                    words_data.append({
                        "word": w.word.strip(),
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 2)
                    })

        full_text = " ".join(full_text_list)

        with open(txt_file, "w", encoding="utf-8") as f:
            f.write(full_text)

        with open(words_file, "w", encoding="utf-8") as f:
            json.dump(words_data, f, ensure_ascii=False, indent=2)

        elapsed = round(time.time() - start_t, 1)
        print(f"✅ [SUCESSO LOCAL] Concluído em {elapsed}s | {len(words_data)} palavras extraídas!")
        print(f"   • Texto salvo em: {txt_file}")

        if cooldown_seconds > 0:
            print(f"❄️ Pausa de resfriamento da CPU ({cooldown_seconds}s)...")
            time.sleep(cooldown_seconds)

        return True
    except Exception as e:
        print(f"❌ [ERRO LOCAL] Falha ao transcrever {audio_path.name}: {e}\n")
        return False


def main():
    parser = argparse.ArgumentParser(description="Script de Transcrição 100% Offline / Local (Zero API)")
    parser.add_argument("audio_path", nargs="?", help="Caminho do áudio local para transcrever")
    parser.add_argument("--all", action="store_true", help="Transcrever todos os cultos locais em lote com pausa")
    parser.add_argument("--model", type=str, default="base", choices=["tiny", "base", "small"], help="Modelo do Whisper (padrão: base)")
    parser.add_argument("--pause", type=int, default=10, help="Segundos de pausa entre cultos (padrão: 10s)")

    args = parser.parse_args()

    print(f"🧠 Carregando Modelo Whisper Local '{args.model}' (CPU int8, ~450MB RAM)...")
    model = WhisperModel(args.model, device="cpu", compute_type="int8")
    print("🟢 Modelo carregado com sucesso no processador local!")

    audio_dir = Path("data/audio_podcasts")

    if args.audio_path:
        target = Path(args.audio_path)
        if not target.exists():
            target = audio_dir / args.audio_path
        transcrever_audio_local(target, model, cooldown_seconds=0)
    elif args.all:
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        print(f"🚀 Processando {len(audios)} cultos locais no modo 100% offline (1 por 1)...")
        for idx, a in enumerate(audios, 1):
            print(f"\n--- [ Culto {idx} de {len(audios)} ] ---")
            transcrever_audio_local(a, model, cooldown_seconds=args.pause)
    else:
        audios = sorted([
            f for f in audio_dir.glob("*")
            if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
        ])
        if not audios:
            print("⚠️ Nenhum arquivo de áudio encontrado em 'data/audio_podcasts'.")
            sys.exit(0)
        
        print("🎯 Transcrevendo apenas o primeiro culto pendente do acervo local...")
        transcrever_audio_local(audios[0], model, cooldown_seconds=0)


if __name__ == "__main__":
    main()
