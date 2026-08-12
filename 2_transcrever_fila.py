"""
======================================================================
 [IBPM CR] AUTOMATION SYSTEM - ETAPA 2: TRANSCRIÇÃO SEQUENCIAL EM FILA
======================================================================

Script de execução exclusiva da ETAPA 2.
Lê os arquivos MP3/M4A salvos no HD local em data/audio_podcasts/ e transcreve em ordem
cronológica (do 1º culto mais antigo em 02/10/2022 ao mais recente) usando faster-whisper
no CPU (device="cpu", compute_type="int8", model_size="base"), salvando o texto e timestamps no SQLite.

Uso:
  python 2_transcrever_fila.py [--batch 10]
"""

import os
import sys
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

# Garante importação do diretório raiz
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config.settings import DB_PATH, AUDIO_DIR
from src.core.state_manager import MasterPlanManager
from src.discovery.transcriber_batch import BatchTranscriber

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Etapa2_Transcricao")


def main():
    parser = argparse.ArgumentParser(description="Etapa 2: Transcrição Sequencial via Faster-Whisper - IBPM CR")
    parser.add_argument("--batch", type=int, default=0, help="Número máximo de cultos a transcrever nesta rodada (0 = todos)")
    args = parser.parse_args()

    print("\n" + "="*75)
    print(" [IBPM CR] AUTOMATION SYSTEM - ETAPA 2: TRANSCRIÇÃO SEQUENCIAL DE ÁUDIO")
    print("   Canal: @ibpmcr7976 | Fila de Transcrição via Faster-Whisper CPU (int8)")
    print(f"   Pasta de Áudios: {AUDIO_DIR}")
    print("="*75 + "\n")

    # 1. Inicializa Gerenciadores
    state_mgr = MasterPlanManager()
    transcriber = BatchTranscriber()

    # 2. Busca lista de vídeos com áudio baixado aguardando transcrição
    pending_list = state_mgr.get_pending_transcriptions()
    total_pending = len(pending_list)

    if total_pending == 0:
        print("✅ Nenhum áudio pendente de transcrição! Todos os cultos baixados já foram transcritos.")
        print("\n👉 PRÓXIMO PASSO: Execute 'python 3_analisar_conteudo.py' para iniciar a mineração PLN!\n")
        return

    print(f"[INFO] Total de {total_pending} cultos com áudio local aguardando transcrição!")

    # 3. Transcreve em ordem cronológica (do mais antigo ao mais recente)
    processed_count = 0

    with tqdm(total=total_pending, desc="Transcrição Faster-Whisper", unit="culto") as pbar:
        for vid in pending_list:
            v_id = vid["video_id"]
            idx = vid.get("indice_sequencial", 0)
            titulo = vid.get("titulo_original", "")
            audio_path = vid.get("caminho_audio") or os.path.join(AUDIO_DIR, f"{v_id}.mp3")

            if args.batch > 0 and processed_count >= args.batch:
                logger.info(f"🛑 Lote de {args.batch} cultos concluído nesta rodada. Pausando para retomada posterior...")
                break

            pbar.set_postfix_str(f"[{idx:03d}] Transcrevendo {v_id}...")

            # Transcreve o arquivo de áudio local
            trans_res = transcriber.transcribe_audio_file(audio_path, video_id=v_id)

            # Salva no SQLite
            full_text = trans_res.get("texto_completo", "")
            segments = trans_res.get("segmentos_timestamps", [])
            tipo_trans = trans_res.get("tipo_transcricao", "audio_real")

            state_mgr.save_transcription(v_id, full_text, segments, tipo_transcricao=tipo_trans)

            processed_count += 1
            pbar.update(1)

    print("\n" + "="*75)
    print(" 🎉 [ETAPA 2 CONCLUÍDA COM SUCESSO!]")
    print(f"   - Cultos Transcritos nesta Rodada: {processed_count}")
    print(f"   - Cultos Pendentes Restantes:       {total_pending - processed_count}")
    print(f"   - Banco SQLite Local:              {DB_PATH}")
    print("="*75)
    print("\n👉 PRÓXIMO PASSO: Execute 'python 3_analisar_conteudo.py' para minerar o PLN dos 25 pilares!\n")


if __name__ == "__main__":
    main()
