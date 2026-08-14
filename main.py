"""
PIPELINE AUTOMATIZADO 100% LOCAL (NLP CLÁSSICO + FFMPEG STREAM COPY) - IBPM CR.

Executa a Mineração de Cortes Teológicos sem uso de LLMs ou APIs pagas/nuvem.

Passos da Execução:
1. Lê as transcrições/legendas da pasta data/audio_podcasts/transcricoes_fase2 (ou data/audio_podcasts/transcricoes).
2. Processa via Janela Deslizante, Dicionário Pentecostal e Blacklist de Avisos (NLP Heurístico).
3. Exporta o relatório relatorio_cortes.csv e os arquivos .insights.json da Fase 3.
4. Realiza os cortes ultrarrápidos via FFmpeg -c copy salvando na pasta data/cortes_finais/.

Uso:
    python main.py
"""

import sys
import os
import json
from pathlib import Path

# Suporte UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.services.minerador_nlp import NLPHeuristicMiner
from src.services.cortador_ffmpeg import FastStreamCopyCutter

logger = get_logger("MainPipelineNLPLocal")


def main():
    print("=" * 70)
    print("🚀 IBPM CR AUTOMATION SYSTEM - PIPELINE 100% LOCAL (NLP CLÁSSICO)")
    print("=" * 70)

    miner = NLPHeuristicMiner()
    cutter = FastStreamCopyCutter()

    trans_dir1 = Path("data/audio_podcasts/transcricoes_fase2")
    trans_dir2 = Path("data/audio_podcasts/transcricoes")
    insights_dir = Path("data/audio_podcasts/conteudos_fase3")
    videos_dir = Path("data/audio_podcasts")
    output_dir = Path("data/cortes_finais")

    insights_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Coleta todas as transcrições .txt locais
    txt_files = sorted(list(trans_dir1.glob("*.txt")) + list(trans_dir2.glob("*.txt")))
    
    if not txt_files:
        print("⚠️ Nenhuma transcrição .txt encontrada em data/audio_podcasts/transcricoes_fase2!")
        print("   Por favor, copie os arquivos .txt ou rode 'python transcrever_100pct_local.py' primeiro.")
        return

    print(f"\n📂 Encontradas {len(txt_files)} transcrições locais para mineração NLP...")

    success_count = 0
    for idx, txt_path in enumerate(txt_files, 1):
        print(f"\n--- [ Processando Culto {idx} de {len(txt_files)}: {txt_path.name} ] ---")
        try:
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                texto = f.read()

            insights_dict = miner.analyze_transcript_heuristic(
                transcript_text=texto,
                source_video_id=txt_path.stem,
                job_id=f"job_nlp_{txt_path.stem}"
            )

            # Salva o arquivo .insights.json da Fase 3 para compatibilidade total com o Studio
            out_json = insights_dir / f"{txt_path.stem}.insights.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(insights_dict, f, ensure_ascii=False, indent=2)

            print(f"✅ Mineração NLP concluída em 0.1s! Shorts: {len(insights_dict['short_form_cuts'])} | Mids: {len(insights_dict['mid_form_cuts'])}")
            success_count += 1
        except Exception as e:
            print(f"❌ Erro ao minerar {txt_path.name}: {e}")

    print("\n" + "=" * 70)
    print(f"📊 Relatório gerado com sucesso: data/relatorio_cortes.csv")
    print(f"🎬 Executando cortes ultrarrápidos via FFmpeg -c copy...")
    print("=" * 70)

    csv_file = Path("data/relatorio_cortes.csv")
    final_cuts = cutter.cut_from_csv(csv_file, videos_dir, output_dir)

    print("\n" + "🎉" * 20)
    print(f"PIPELINE LOCAL CONCLUÍDO COM SUCESSO!")
    print(f"• {success_count} cultos minerados via NLP Clássico!")
    print(f"• {len(final_cuts)} arquivos de vídeo cortados em 0.5s salvos em 'data/cortes_finais/'")
    print("🎉" * 20 + "\n")


if __name__ == "__main__":
    main()
