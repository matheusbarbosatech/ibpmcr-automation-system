"""
Script Principal da FASE 3: Hub Inteligente de Mineração de Conteúdo (Groq Open-Source Cloud API).

Lê os arquivos de transcrição (.txt e .json) da pasta data/audio_podcasts/ (ou Google Drive),
envia o conteúdo para os modelos Open-Source na nuvem do Groq (Llama 3.3 70B, Qwen 2.5 72B, DeepSeek R1)
e gera os relatórios de insights em JSON e no SQLite.

Requisitos Atendidos:
1. Suporte a caminhos locais ou sincronizados do Google Drive (G:\Meu Drive\IBPM_CR_Cortes).
2. Idempotência: pula cultos que já possuem relatório gerado no destino e no banco SQLite.
3. Extração dos 6 pilares: Tema Central, Frases Virais, Passagens Bíblicas, Carrossel Instagram, Cortes Virais e Prompt Thumbnail.
4. Gravação individual em arquivo .json no destino e inserção na tabela acervo_insights do SQLite.
"""

import sys
import os
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

from config.settings import AUDIO_DIR, INSIGHTS_DIR, DB_PATH, GROQ_API_KEY
from src.core.state_manager import MasterPlanManager
from src.discovery.content_miner_llm import ContentMinerLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Fase3_MineracaoConteudo")


def print_banner():
    banner = f"""
===========================================================================
 [IBPM CR] AUTOMATION SYSTEM - FASE 3: MINERAÇÃO INTELIGENTE (GROQ OPEN-SOURCE)
   Modelos na Nuvem:   Llama 3.3 70B | Qwen 2.5 72B | DeepSeek R1 70B
   Origem Transcrições: {AUDIO_DIR}
   Destino Insights:    {INSIGHTS_DIR}
   Banco de Dados:      {DB_PATH}
   Papel do Modelo:     Curador de Conteúdo & Teólogo Sênior
===========================================================================
    """
    print(banner)


def main():
    parser = argparse.ArgumentParser(description="Fase 3 - Mineração de Conteúdo via Groq Open-Source API")
    parser.add_argument("--batch-size", type=int, default=10, help="Quantidade de cultos a minerar por lote (padrão: 10)")
    parser.add_argument("--force", action="store_true", help="Forçar re-mineração mesmo se o relatório já existir")
    args = parser.parse_args()

    print_banner()

    state_mgr = MasterPlanManager()
    miner = ContentMinerLLM(groq_api_key=GROQ_API_KEY)

    all_videos = state_mgr.get_all_videos_chronological()
    
    pending_list = []
    skipped = 0

    for v in all_videos:
        v_id = v["video_id"]
        idx = v.get("indice_sequencial", 1)

        # Localiza o arquivo .txt da transcrição
        txt_file = None
        if os.path.exists(AUDIO_DIR):
            for fname in os.listdir(AUDIO_DIR):
                if v_id in fname and fname.endswith(".txt"):
                    full_txt_p = os.path.join(AUDIO_DIR, fname)
                    if os.path.getsize(full_txt_p) > 50:
                        txt_file = full_txt_p
                        break

        if not txt_file and v.get("texto_transcrito") and len(v.get("texto_transcrito").strip()) > 50:
            txt_file = f"sqlite_video_{v_id}"

        if not txt_file:
            continue

        date_str = str(v.get("data_publicacao", ""))[:10]
        sanitized = v.get("titulo_sanitizado", "culto")
        out_json_path = INSIGHTS_DIR / f"{idx:03d}_{date_str}_{v_id}_{sanitized}.insights.json"

        already_done = (
            not args.force and
            out_json_path.exists() and
            out_json_path.stat().st_size > 100 and
            state_mgr.is_insight_processed(v_id)
        )

        if already_done:
            skipped += 1
        else:
            v["txt_file_path"] = txt_file
            v["out_json_path"] = out_json_path
            pending_list.append(v)

    logger.info(f"📋 Fila da Fase 3: {len(pending_list)} cultos pendentes (Já minerados: {skipped}).")

    if not pending_list:
        logger.info("🎉 Todos os cultos da fila já possuem relatórios de insights gerados na Fase 3!")
        return

    items_to_process = pending_list[:args.batch_size]
    pbar = tqdm(items_to_process, desc="Minerando Insights via Groq LLM", unit="culto")

    processed_count = 0

    for item in pbar:
        v_id = item["video_id"]
        idx = item.get("indice_sequencial", 1)
        title = item.get("titulo_original", "")
        txt_path = item["txt_file_path"]
        out_json_path = item["out_json_path"]

        display_name = f"[{idx:03d}] {v_id} - {title[:25]}"
        pbar.set_postfix_str(display_name)

        if txt_path.startswith("sqlite_video_"):
            text_content = item.get("texto_transcrito", "")
        else:
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            except Exception as e:
                logger.warning(f"⚠️ Erro ao ler arquivo .txt {txt_path}: {e}")
                continue

        logger.info(f"\n🧠 Processando vídeo [{idx:03d}] (ID: {v_id}) via Groq Open-Source LLM...")

        insights_dict = miner.mine_transcription(text_content=text_content, title=title)

        if insights_dict:
            raw_json_str = json.dumps(insights_dict, ensure_ascii=False, indent=2)

            try:
                with open(out_json_path, "w", encoding="utf-8") as f:
                    f.write(raw_json_str)
                logger.info(f"📄 Relatório de Insights salvo em: {out_json_path}")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao salvar arquivo JSON no disco: {e}")

            state_mgr.save_insights_fase3(
                video_id=v_id,
                idx=idx,
                title=title,
                insights_dict=insights_dict,
                raw_json=raw_json_str
            )
            logger.info(f"💾 Insights salvos na tabela acervo_insights do SQLite para {v_id}.")

            processed_count += 1

    print("\n" + "=" * 75)
    print(" RESUMO DA EXECUÇÃO DA FASE 3:")
    print(f"   • Cultos Minerados no Lote: {processed_count}")
    print(f"   • Pasta de Origem:           {AUDIO_DIR}")
    print(f"   • Pasta de Destino Insights: {INSIGHTS_DIR}")
    print(f"   • Banco SQLite Atualizado:   {DB_PATH}")
    print("=" * 75)
    print(" [FASE 3 CONCLUÍDA COM SUCESSO!]")
    print(" Para exportar o JSON Mestre e Relatórios executivos em PDF/HTML, rode: python 4_gerar_relatorio.py")
    print("=" * 75 + "\n")


if __name__ == "__main__":
    main()
