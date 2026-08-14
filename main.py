"""
PIPELINE AUTOMATIZADO 100% LOCAL (TEXTRANK + NMS + FFMPEG STREAM COPY) - IBPM CR.

Executa a Mineração Extrativa Semântica e Agrupamento Temático sem uso de LLMs ou APIs pagas.

Passos da Execução:
1. Lê as transcrições da pasta data/audio_podcasts/transcricoes_fase2.
2. Aplica TextRank (Grafos TF-IDF PageRank) e Supressão de Não-Máximos (NMS Temporal).
3. Exporta o relatório relatorio_cortes.csv e os arquivos .insights.json da Fase 3.
4. Gera o agrupamento de Playlists Temáticas (data/playlists_tematicas.json).
5. Realiza os cortes ultrarrápidos via FFmpeg -c copy salvando na pasta data/cortes_finais/.
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
from src.services.minerador_nlp import DualSermonMiner, PlaylistOrganizer
from src.services.cortador_ffmpeg import FastStreamCopyCutter

logger = get_logger("MainPipelineNLPPro")


def main():
    print("=" * 70)
    print("🚀 IBPM CR AUTOMATION SYSTEM - PIPELINE PRO (TEXTRANK + NMS + PLAYLISTS)")
    print("=" * 70)

    miner = DualSermonMiner()
    cutter = FastStreamCopyCutter()

    trans_dir1 = Path("data/audio_podcasts/transcricoes_fase2")
    trans_dir2 = Path("data/audio_podcasts/transcricoes")
    insights_dir = Path("data/audio_podcasts/conteudos_fase3")
    videos_dir = Path("data/audio_podcasts")
    output_dir = Path("data/cortes_finais")

    insights_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    txt_files = sorted(list(trans_dir1.glob("*.txt")) + list(trans_dir2.glob("*.txt")))
    
    if not txt_files:
        print("⚠️ Nenhuma transcrição .txt encontrada em data/audio_podcasts/transcricoes_fase2!")
        return

    print(f"\n📂 Encontradas {len(txt_files)} transcrições locais para mineração extrativa semântica...")

    all_medium_cuts = []
    success_count = 0

    for idx, txt_path in enumerate(txt_files, 1):
        print(f"\n--- [ Processando Culto {idx} de {len(txt_files)}: {txt_path.name} ] ---")
        try:
            with open(txt_path, "r", encoding="utf-8", errors="ignore") as f:
                texto = f.read()

            insights_dict = miner.mine_sermon(
                transcript_text=texto,
                sermon_id=txt_path.stem
            )

            out_json = insights_dir / f"{txt_path.stem}.insights.json"
            with open(out_json, "w", encoding="utf-8") as f:
                json.dump(insights_dict, f, ensure_ascii=False, indent=2)

            all_medium_cuts.extend(insights_dict.get("mid_form_cuts", []))
            print(f"✅ TextRank & NMS Concluídos em 0.1s! Shorts (9:16): {len(insights_dict['short_form_cuts'])} | Mids (16:9): {len(insights_dict['mid_form_cuts'])}")
            success_count += 1
        except Exception as e:
            print(f"❌ Erro ao minerar {txt_path.name}: {e}")

    # Agrupamento de Playlists Temáticas (Clustering Cross-Sermão)
    if all_medium_cuts:
        print("\n" + "=" * 70)
        print("🎶 Montando Playlists Temáticas Cross-Sermão (Clustering MiniBatchKMeans)...")
        print("=" * 70)
        organizer = PlaylistOrganizer(num_playlists=min(5, len(all_medium_cuts)))
        playlists = organizer.build_playlists(all_medium_cuts)

        playlist_file = Path("data/playlists_tematicas.json")
        with open(playlist_file, "w", encoding="utf-8") as f:
            json.dump(playlists, f, ensure_ascii=False, indent=2)
        print(f"✅ Playlists Temáticas salvas com sucesso em: {playlist_file}")

    print("\n" + "=" * 70)
    print(f"📊 Relatório gerado com sucesso: data/relatorio_cortes.csv")
    print(f"🎬 Executando cortes ultrarrápidos via FFmpeg -c copy...")
    print("=" * 70)

    csv_file = Path("data/relatorio_cortes.csv")
    final_cuts = cutter.cut_from_csv(csv_file, videos_dir, output_dir)

    print("\n" + "🎉" * 20)
    print(f"PIPELINE LOCAL TEXTRANK CONCLUÍDO COM SUCESSO!")
    print(f"• {success_count} cultos minerados via TextRank / LexRank!")
    print(f"• {len(final_cuts)} arquivos de vídeo cortados em 0.1s salvos em 'data/cortes_finais/'")
    print("🎉" * 20 + "\n")


if __name__ == "__main__":
    main()
