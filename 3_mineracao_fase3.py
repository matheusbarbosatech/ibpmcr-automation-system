"""
Script Principal da FASE 3: Hub Inteligente de Mineração de Conteúdo (Gemini 1.5 Flash com Monitoramento Contínuo).

Monitora continuamente a pasta de transcrições (G:\\Meu Drive\\IBPM_CR_Cortes\\audio_podcasts\\transcricoes\\).
Assim que o Google Colab conclui a transcrição de um culto (gerando .txt e .json), este script detecta automaticamente,
envia para o Gemini 1.5 Flash (com Freio ABS de 4.5s), anota os timestamps exatos dos cortes virais,
e salva os relatórios em audio_podcasts/conteudos_fase3/ e no SQLite de forma 100% autônoma!

Uso no Terminal Local:
   python 3_mineracao_fase3.py --watch
   (ou sem --watch para rodar um lote único)
"""

import sys
import os
import time
import json
import argparse
import logging
from pathlib import Path
from tqdm import tqdm

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import AUDIO_DIR, TRANSCRICOES_DIR, INSIGHTS_DIR, DB_PATH, GEMINI_API_KEY, GROQ_API_KEY
from src.core.state_manager import MasterPlanManager
from src.discovery.content_miner_llm import ContentMinerLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Fase3_MineracaoConteudo")


def print_banner(watch_mode: bool = False):
    modo_str = "MONITORAMENTO CONTÍNUO (DAEMON WATCHDOG)" if watch_mode else "LOTE ÚNICO"
    banner = f"""
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - FASE 3: MINERAÇÃO DE CONTEÚDO CONTINUA
   Modo de Execução:    {modo_str}
   IA Principal:        Google Gemini 1.5 Flash (Freio ABS de 4.5s / 15 RPM)
   IA Fallback:         Groq Cloud API (Llama 3.3 70B Open-Source)
   Origem Transcrições: {TRANSCRICOES_DIR}
   Destino Conteúdos:   {INSIGHTS_DIR}
   Banco de Dados:      {DB_PATH}
===========================================================================
    """
    print(banner)


def process_pending_batch(state_mgr: MasterPlanManager, miner: ContentMinerLLM, max_items: int = 50, force: bool = False) -> int:
    txt_files = []
    if TRANSCRICOES_DIR.exists():
        txt_files = sorted([f for f in TRANSCRICOES_DIR.glob("*.txt") if f.stat().st_size > 100])
    
    if not txt_files and AUDIO_DIR.exists():
        txt_files = sorted([f for f in AUDIO_DIR.glob("*.txt") if f.stat().st_size > 100])

    pending_list = []
    skipped = 0

    for txt_path in txt_files:
        stem = txt_path.stem
        json_path = txt_path.with_suffix(".json")
        out_json_path = INSIGHTS_DIR / f"{stem}.insights.json"

        already_done = (
            not force and
            out_json_path.exists() and
            out_json_path.stat().st_size > 100
        )

        if already_done:
            skipped += 1
        else:
            pending_list.append((stem, txt_path, json_path, out_json_path))

    if not pending_list:
        return 0

    items_to_process = pending_list[:max_items]
    pbar = tqdm(items_to_process, desc="Minerando Transcrições (.txt + .json)", unit="culto")

    processed_count = 0

    for stem, txt_path, json_path, out_json_path in pbar:
        display_name = f"{stem[:30]}"
        pbar.set_postfix_str(display_name)

        # 1. Lê o texto integral (.txt)
        text_content = ""
        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler arquivo .txt {txt_path}: {e}")
            continue

        # 2. Lê os segmentos com timestamps (.json) se existir
        segments_data = None
        if json_path.exists() and json_path.stat().st_size > 50:
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    segments_data = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Erro ao ler arquivo de segmentos .json {json_path}: {e}")

        logger.info(f"\n🧠 [FASE 3] Minerando pregação '{stem}' via Gemini 1.5 Flash...")

        insights_dict = miner.mine_transcription(text_content=text_content, segments_data=segments_data, title=stem)

        if insights_dict:
            raw_json_str = json.dumps(insights_dict, ensure_ascii=False, indent=2)

            try:
                with open(out_json_path, "w", encoding="utf-8") as f:
                    f.write(raw_json_str)
                logger.info(f"📄 Relatório de Conteúdos salvo em: {out_json_path}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar arquivo JSON no disco: {e}")

            v_id = stem.split("_")[2] if len(stem.split("_")) > 2 else stem
            state_mgr.save_insights_fase3(
                video_id=v_id,
                idx=1,
                title=stem,
                insights_dict=insights_dict,
                raw_json=raw_json_str
            )
            logger.info(f"💾 Insights e Timestamps dos Cortes salvos no SQLite para {v_id}.")

            processed_count += 1

    return processed_count


def main():
    parser = argparse.ArgumentParser(description="Fase 3 - Mineração de Conteúdo via Gemini 1.5 Flash API com Monitoramento Contínuo")
    parser.add_argument("--batch-size", type=int, default=50, help="Quantidade de cultos a minerar por lote (padrão: 50)")
    parser.add_argument("--watch", action="store_true", help="Manter o script monitorando continuamente a pasta de transcrições do Drive")
    parser.add_argument("--force", action="store_true", help="Forçar re-mineração mesmo se o relatório já existir")
    args = parser.parse_args()

    print_banner(watch_mode=args.watch or True)

    state_mgr = MasterPlanManager()
    miner = ContentMinerLLM(gemini_api_key=GEMINI_API_KEY, groq_api_key=GROQ_API_KEY)

    # Execução em loop de monitoramento contínuo
    logger.info("👀 Bot da Fase 3 Iniciado! Monitorando a pasta de transcrições do Google Drive...\n")

    while True:
        try:
            processed = process_pending_batch(state_mgr, miner, max_items=args.batch_size, force=args.force)

            if not args.watch and processed > 0:
                logger.info(f"✅ Processamento de lote concluído ({processed} cultos minerados). Exibindo resumo.")
                break
            
            if processed == 0:
                logger.info("😴 Nenhum novo arquivo de transcrição pendente no momento. Aguardando o Colab transcrever mais cultos (Checando em 15s)...")
                time.sleep(15)

        except KeyboardInterrupt:
            logger.info("\n🛑 Monitoramento da Fase 3 encerrado pelo usuário.")
            break
        except Exception as e:
            logger.warning(f"⚠️ Ocorreu um erro inesperado no monitoramento da Fase 3: {e}. Reiniciando ciclo em 10s...")
            time.sleep(10)


if __name__ == "__main__":
    main()
