"""
Script Principal da FASE 3: Hub Inteligente de Mineração de Conteúdo (Gemini 1.5 Flash / Groq LLM).

Lê os arquivos de transcrição (.txt) E os segmentos detalhados (.json) da Fase 2 na subpasta audio_podcasts/transcricoes/,
envia o conteúdo para a API do Google Gemini 1.5 Flash (com Freio ABS de 4.5s / 15 RPM),
cruza o texto com os segmentos para anotar os timestamps exatos (start_sec e end_sec) dos cortes virais,
e salva os relatórios em .insights.json na subpasta audio_podcasts/conteudos_fase3/ e no SQLite.

Uso no Terminal Local:
   python 3_mineracao_fase3.py
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


def print_banner():
    banner = f"""
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - FASE 3: MINERAÇÃO INTELIGENTE (TXT + JSON)
   IA Principal:        Google Gemini 1.5 Flash (Com Freio ABS de 4.5s / 15 RPM)
   IA Fallback:         Groq Cloud API (Llama 3.3 70B Open-Source)
   Entrada de Dados:    .txt (Texto Integral) + .json (Timestamps de Segmentos)
   Origem Transcrições: {TRANSCRICOES_DIR}
   Destino Conteúdos:   {INSIGHTS_DIR}
   Banco de Dados:      {DB_PATH}
===========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Fase 3 - Mineração de Conteúdo via Gemini 1.5 Flash API com cruzamento de Timestamps .json")
    parser.add_argument("--batch-size", type=int, default=50, help="Quantidade de cultos a minerar por lote (padrão: 50)")
    parser.add_argument("--force", action="store_true", help="Forçar re-mineração mesmo se o relatório já existir")
    args = parser.parse_args()

    print_banner()

    state_mgr = MasterPlanManager()
    miner = ContentMinerLLM(gemini_api_key=GEMINI_API_KEY, groq_api_key=GROQ_API_KEY)

    # Mapeia todos os arquivos .txt na pasta de transcrições
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
            not args.force and
            out_json_path.exists() and
            out_json_path.stat().st_size > 100
        )

        if already_done:
            skipped += 1
        else:
            pending_list.append((stem, txt_path, json_path, out_json_path))

    logger.info(f"📋 Fila da Fase 3 Local: {len(pending_list)} transcrições (.txt+.json) pendentes (Já concluídas: {skipped}).")

    if not pending_list:
        logger.info("🎉 Todas as transcrições disponíveis já possuem relatórios de insights gerados na Fase 3!")
        return

    items_to_process = pending_list[:args.batch_size]
    pbar = tqdm(items_to_process, desc="Minerando Insights (.txt + .json)", unit="culto")

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

        logger.info(f"\n🧠 Minerando pregação '{stem}' (.txt + .json)...")

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

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA FASE 3:")
    print(f"   • Cultos Minerados no Lote: {processed_count}")
    print(f"   • Transcrições (.txt+.json): {TRANSCRICOES_DIR}")
    print(f"   • Conteúdos (.insights.json):{INSIGHTS_DIR}")
    print(f"   • Banco SQLite Atualizado:   {DB_PATH}")
    print("=" * 75)
    print(" [FASE 3 CONCLUÍDA COM SUCESSO! CORTES PRONTOS PARA A FASE 4!]")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
