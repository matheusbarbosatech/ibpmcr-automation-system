"""
Script Oficial da Fase 3 Renderização - Renderização Audiovisual & Geração de Copy para Redes Sociais - IBPM CR Automation System.

Executa:
1. Corte e Edição Audiovisual (Stream Copy ultrarrápido -c copy ou Re-encoding Studio 9:16 Vertical com legendas Karaokê .ASS e EBU R128).
2. Geração de Metadados e Copy de Postagens para Instagram Reels, YouTube Shorts e TikTok (Títulos, Captions, Hashtags e Grade de Agendamento).
"""

import sys
import os
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger
from src.services.cortador_ffmpeg import FastStreamCopyCutter, parse_timestamp_to_seconds
from src.infrastructure.ffmpeg_client import FFmpegClient

logger = get_logger("ExecutarFase3Renderizacao")


def gerar_copys_postagem(cortes_info: List[Dict[str, Any]], output_json: Path, output_txt: Path) -> List[Dict[str, Any]]:
    """
    Gera títulos chamativos, legendas completas, hashtags teológicas e grade de agendamento.
    """
    logger.info("✍️ Gerando Copy e Metadados de Postagem para Redes Sociais...")
    postagens = []
    
    start_date = datetime.now() + timedelta(days=1)
    horarios = ["08:00", "12:30", "19:00"]
    post_idx = 0

    for item in cortes_info:
        c_id = item.get("corte_id", "short_001")
        origem = item.get("arquivo_origem", "culto")
        dur = item.get("duracao_segundos", 45)
        score = item.get("score", 100)
        texto = item.get("texto_do_corte", "")

        # Títulos virais baseados no tipo de corte
        if "short" in str(c_id).lower():
            titulo = f"🔥 UMA PALAVRA FORTE PARA A SUA VIDA! ({c_id})"
            hook = "Ouça o que Deus tem para falar com você hoje! 📖✨"
        else:
            titulo = f"📖 ESTUDO BÍBLICO E EXEGESE PROFUNDA ({c_id})"
            hook = "Assista a esta exposição da Palavra de Deus! 🙏"

        # Agendamento sequencial
        dia_post = start_date + timedelta(days=post_idx // 3)
        horario_post = horarios[post_idx % 3]
        data_agendamento = f"{dia_post.strftime('%Y-%m-%d')} às {horario_post}"

        caption = f"""{titulo}

{hook}

"Onde há a pregação pura da Palavra, ali está a presença de Deus."

💬 Deixe seu AMÉM nos comentários!
📲 Compartilhe esta mensagem com alguém que precisa ouvir isso hoje!
🔔 Siga a @ibpmcr para mais conteúdos edificantes.

---
#IBPMCR #Pregação #PalavraDeDeus #Jesus #Fé #Evangelho #ReelsCristao #Shorts #Biblia #MensagemDeFe
"""

        post_data = {
            "corte_id": c_id,
            "arquivo_origem": origem,
            "duracao_segundos": dur,
            "score": score,
            "titulo_viral": titulo,
            "hook_subtitulo": hook,
            "data_agendamento_sugerida": data_agendamento,
            "legenda_completa": caption.strip(),
            "hashtags": ["#IBPMCR", "#Pregação", "#PalavraDeDeus", "#Jesus", "#Fé", "#Evangelho", "#Shorts", "#Reels"]
        }
        postagens.append(post_data)
        post_idx += 1

    # Salva JSON estruturado
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(postagens, f, ensure_ascii=False, indent=2)

    # Salva TXT formatado para leitura humana
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("====================================================\n")
        f.write("   IBPM CR - GRADE DE POSTAGENS E COPYS DAS REDES   \n")
        f.write("====================================================\n\n")
        for p in postagens:
            f.write(f"📌 CORTE: {p['corte_id']} ({p['arquivo_origem']})\n")
            f.write(f"📅 AGENDAMENTO: {p['data_agendamento_sugerida']}\n")
            f.write(f"🎯 TÍTULO: {p['titulo_viral']}\n")
            f.write("----------------------------------------------------\n")
            f.write(f"{p['legenda_completa']}\n")
            f.write("====================================================\n\n")

    logger.info(f"✅ Copy de {len(postagens)} postagens gerada com sucesso em '{output_json}' e '{output_txt}'.")
    return postagens


def executar_fase3_renderizacao(modo: str = "stream_copy", max_cortes: int = 50):
    """
    Executa a Fase 3 Renderização completa.
    """
    logger.info(f"🚀 Iniciando FASE 3 RENDERIZAÇÃO: Renderização Audiovisual (Modo: {modo.upper()})")

    csv_file = Path("data/audio_podcasts/conteudos_fase2/relatorio_cortes.csv")
    if not csv_file.exists():
        csv_file = Path("data/relatorio_cortes.csv")

    videos_dir = Path("data/audio_podcasts")
    output_stream_copy = Path("data/audio_podcasts/conteudos_fase2/cortes_finais")
    output_studio_video = Path("data/audio_podcasts/conteudos_fase2/cortes_finais_video")
    json_postagens = Path("data/audio_podcasts/conteudos_fase2/postagens_redes_sociais.json")
    txt_postagens = Path("data/audio_podcasts/conteudos_fase2/postagens_redes_sociais.txt")

    if not csv_file.exists():
        logger.error(f"❌ Arquivo '{csv_file}' não encontrado. Execute a Fase 2 Mineração primeiro (python executar_fase2_mineracao.py).")
        return

    cortes_info = []
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for idx, row in enumerate(reader):
            if idx >= max_cortes:
                break
            cortes_info.append(row)

    logger.info(f"📊 {len(cortes_info)} cortes carregados do relatório da Fase 2 Mineração.")

    # 1. Executa corte ultrarrápido Stream Copy (-c copy)
    if modo in ["stream_copy", "full"]:
        cutter = FastStreamCopyCutter()
        cuts_copy = cutter.cut_from_csv(csv_file, videos_dir, output_stream_copy)
        logger.info(f"✅ {len(cuts_copy)} arquivos cortados via Stream Copy em '{output_stream_copy}'.")

    # 2. Executa renderização 9:16 Studio Pro Vertical com FFmpeg
    if modo in ["studio_9x16", "full"]:
        ffmpeg = FFmpegClient()
        output_studio_video.mkdir(parents=True, exist_ok=True)
        rendered_count = 0

        for row in cortes_info:
            orig = row.get("sermon_id", row.get("arquivo_origem", ""))
            c_id = row.get("corte_id", row.get("tipo", "short"))
            ts_in = str(row.get("start_time", row.get("timestamp_inicio", "00:00:00")))
            dur = float(row.get("duracao", row.get("duracao_segundos", "45")))
            
            src_file = None
            for ext in [".mp4", ".webm", ".mkv", ".mp3", ".wav"]:
                p = videos_dir / f"{orig}{ext}"
                if p.exists():
                    src_file = p
                    break

            if not src_file:
                logger.debug(f"Mídia de vídeo/áudio para '{orig}' não encontrada para re-encoding 9:16. Pulando modo Studio.")
                continue

            out_video = output_studio_video / f"{orig}_{c_id}_9x16.mp4"
            start_sec = float(ts_in) if ts_in.replace('.', '', 1).isdigit() else parse_timestamp_to_seconds(ts_in)
            end_sec = start_sec + dur

            try:
                ffmpeg.render_short_form(
                    video_input=src_file,
                    output_path=out_video,
                    start_sec=start_sec,
                    end_sec=end_sec,
                    job_id=f"job_{c_id}"
                )
                rendered_count += 1
            except Exception as e:
                logger.error(f"Erro ao renderizar 9:16 para {out_video.name}: {e}")

        logger.info(f"🎬 {rendered_count} vídeos 9:16 Studio Pro renderizados em '{output_studio_video}'.")

    # 3. Gera Copy e Metadados de Postagem
    gerar_copys_postagem(cortes_info, json_postagens, txt_postagens)

    print("\n" + "=" * 60)
    print(" FASE 3 RENDERIZAÇÃO E PRODUÇÃO CONCLUÍDA COM SUCESSO!")
    print(f" * Modo executado: {modo}")
    print(f" * Cortes gerados em: '{output_stream_copy}'")
    print(f" * Grade e Copys salvas em: '{json_postagens}' e '{txt_postagens}'")
    print("=" * 60 + "\n")


executar_fase4 = executar_fase3_renderizacao


def main():
    parser = argparse.ArgumentParser(description="Executar Fase 3 - Renderização e Produção de Cortes IBPM CR")
    parser.add_argument("--modo", choices=["stream_copy", "studio_9x16", "full"], default="stream_copy",
                        help="Modo de processamento (stream_copy = 0.1s instantâneo, studio_9x16 = 9:16 vertical, full = ambos)")
    parser.add_argument("--max", type=int, default=50, help="Quantidade máxima de cortes a processar")
    args = parser.parse_args()

    executar_fase3_renderizacao(modo=args.modo, max_cortes=args.max)


if __name__ == "__main__":
    main()
