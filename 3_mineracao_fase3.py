"""
Script Principal da FASE 3: Hub Inteligente de Mineração de Conteúdo (Gemini 1.5 Flash / Groq LLM).

Lê os arquivos de transcrição (.txt e .json) gerados pela Fase 2 na subpasta audio_podcasts/transcricoes/,
envia o conteúdo para a API do Google Gemini 1.5 Flash (com Freio ABS de 4.5s / 15 RPM) ou Groq Llama 3.3 70B,
e salva os relatórios de insights em .insights.json na subpasta audio_podcasts/conteudos_fase3/ e no SQLite.

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
 [IBPM CR] AUTOMATION SYSTEM - FASE 3: MINERAÇÃO DE CONTEÚDO (GEMINI 1.5 FLASH)
   IA Principal:        Google Gemini 1.5 Flash (Com Freio ABS de 4.5s / 15 RPM)
   IA Fallback:         Groq Cloud API (Llama 3.3 70B Open-Source)
   Origem Transcrições: {TRANSCRICOES_DIR}
   Destino Conteúdos:   {INSIGHTS_DIR}
   Banco de Dados:      {DB_PATH}
   Papel do Modelo:     Curador de Conteúdo & Teólogo Sênior
===========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Fase 3 - Mineração de Conteúdo via Gemini 1.5 Flash API")
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
    
    # Fallback para AUDIO_DIR caso estejam no diretório raiz de áudios
    if not txt_files and AUDIO_DIR.exists():
        txt_files = sorted([f for f in AUDIO_DIR.glob("*.txt") if f.stat().st_size > 100])

    pending_list = []
    skipped = 0

    for txt_path in txt_files:
        stem = txt_path.stem
        out_json_path = INSIGHTS_DIR / f"{stem}.insights.json"

        already_done = (
            not args.force and
            out_json_path.exists() and
            out_json_path.stat().st_size > 100
        )

        if already_done:
            skipped += 1
        else:
            pending_list.append((stem, txt_path, out_json_path))

    logger.info(f"📋 Fila da Fase 3 Local: {len(pending_list)} transcrições pendentes para mineração (Já concluídas: {skipped}).")

    if not pending_list:
        logger.info("🎉 Todas as transcrições disponíveis já possuem relatórios de insights gerados na Fase 3!")
        return

    items_to_process = pending_list[:args.batch_size]
    pbar = tqdm(items_to_process, desc="Minerando Insights (Gemini 1.5 Flash)", unit="culto")

    processed_count = 0

    for stem, txt_path, out_json_path in pbar:
        display_name = f"{stem[:30]}"
        pbar.set_postfix_str(display_name)

        try:
            with open(txt_path, "r", encoding="utf-8") as f:
                text_content = f.read()
        except Exception as e:
            logger.warning(f"⚠️ Erro ao ler arquivo .txt {txt_path}: {e}")
            continue

        logger.info(f"\n🧠 Minerando pregação '{stem}' via Gemini 1.5 Flash...")

        insights_dict = miner.mine_transcription(text_content=text_content, title=stem)

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
            logger.info(f"💾 Insights sincronizados no banco SQLite para {v_id}.")

            processed_count += 1

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA FASE 3:")
    print(f"   • Cultos Minerados no Lote: {processed_count}")
    print(f"   • Origem Transcrições:       {TRANSCRICOES_DIR}")
    print(f"   • Destino Conteúdos:         {INSIGHTS_DIR}")
    print(f"   • Banco SQLite Atualizado:   {DB_PATH}")
    print("=" * 75)
    print(" [FASE 3 CONCLUÍDA COM SUCESSO!]")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
