"""
Script da FASE 4: O Sniper / Motor de Edição Automatizada com Download Cirúrgico.
Lê o JSON (Timeline Execution Payload), calcula os tempos exatos via Whisper,
baixa APENAS O TRECHO necessário do YouTube via yt-dlp e prepara o arquivo para renderização.
"""

import sys
import os
import json
import subprocess
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Fase4_Sniper")


def baixar_trecho_youtube(youtube_id: str, start_sec: float, end_sec: float, output_path: Path):
    """
    Usa o yt-dlp para baixar diretamente do YouTube apenas o intervalo de segundos necessário,
    economizando gigabytes de espaço e tempo de download!
    """
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    
    # Adiciona uma margem de segurança de 2 segundos antes e depois
    start_m = max(0, start_sec - 2)
    duration = (end_sec - start_sec) + 4
    end_m = start_m + duration
    
    logger.info(f"📥 Baixando trecho cirúrgico do YouTube (ID: {youtube_id}) das {start_m:.1f}s até {end_m:.1f}s (Duração: {duration:.1f}s)...")
    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Tenta usar a CLI 'yt-dlp' ou o módulo python 'python -m yt_dlp'
    cmd = [
        "yt-dlp",
        "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
        "--download-sections", f"*{start_m:.1f}-{end_m:.1f}",
        "-o", str(output_path),
        url
    ]
    
    try:
        subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        logger.info(f"✅ Trecho baixado com sucesso: {output_path.name}")
        return True
    except Exception as e1:
        # Fallback usando o executável python do ambiente virtual
        logger.warning(f"⚠️ Aviso ao rodar CLI yt-dlp direto ({e1}). Tentando via 'python -m yt_dlp'...")
        cmd_fallback = [
            sys.executable, "-m", "yt_dlp",
            "-f", "bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--download-sections", f"*{start_m:.1f}-{end_m:.1f}",
            "-o", str(output_path),
            url
        ]
        try:
            subprocess.run(cmd_fallback, check=True)
            logger.info(f"✅ Trecho baixado com sucesso via python module: {output_path.name}")
            return True
        except Exception as e2:
            logger.error(f"❌ Erro ao baixar o trecho do YouTube: {e2}")
            return False


def encontrar_timestamps_por_ancoras(transcricao_json_path: Path, ancora_inicial: str, ancora_final: str):
    """
    Cruza as âncoras de texto com o arquivo .json original da Fase 2 (Whisper)
    para extrair o start_sec e o end_sec milimétricos, eliminando alucinações da IA.
    """
    if not transcricao_json_path.exists():
        logger.warning(f"⚠️ Arquivo de transcrição não encontrado: {transcricao_json_path}")
        return 0.0, 45.0
        
    with open(transcricao_json_path, "r", encoding="utf-8") as f:
        segmentos = json.load(f)
        
    start_sec = None
    end_sec = None
    
    palavras_ini = [w.lower() for w in ancora_inicial.split() if w]
    palavras_fim = [w.lower() for w in ancora_final.split() if w]
    
    for seg in segmentos:
        texto_bloco = seg.get("text", "").lower()
        
        if start_sec is None and palavras_ini:
            if any(p in texto_bloco for p in palavras_ini[:3]):
                start_sec = seg.get("start_sec", seg.get("start", 0.0))
                
        if start_sec is not None and palavras_fim:
            if any(p in texto_bloco for p in palavras_fim[-3:]):
                end_sec = seg.get("end_sec", seg.get("end", start_sec + 30.0))
                break
            
    return float(start_sec if start_sec is not None else 0.0), float(end_sec if end_sec is not None else 45.0)


def processar_fase_4(payload_json: dict, transcricao_json_path: Path, youtube_id: str):
    logger.info("===========================================================================")
    logger.info(" 🎯 [FASE 4] INICIANDO O SNIPER DE VÍDEOS COM DOWNLOAD CIRÚRGICO DO YOUTUBE")
    logger.info("===========================================================================\n")
    
    pasta_saida = Path("data/audio_podcasts/cortes_fase4")
    pasta_saida.mkdir(parents=True, exist_ok=True)
    
    # Suporta estruturas de payload (Enterprise Timeline, Render Queue ou Legacy)
    shorts_queue = (
        payload_json.get("02_short_form_render_queue") or
        payload_json.get("02_cortes_curtos_shorts") or
        payload_json.get("cortes_selecionados") or
        payload_json.get("05_cortes_virais") or []
    )
    
    if not shorts_queue:
        logger.warning("⚠️ Nenhum corte encontrado no payload fornecido!")
        return

    for idx, item in enumerate(shorts_queue, 1):
        export_id = item.get("export_id") or item.get("id_referencia") or item.get("id_corte") or f"short_{idx:02d}"
        
        ext_data = item.get("extraction_data", {})
        ancora_ini = ext_data.get("anchor_start") or item.get("ancora_inicial_exata") or item.get("trecho_inicial") or ""
        ancora_fim = ext_data.get("anchor_end") or item.get("ancora_final_exata") or item.get("trecho_final") or ""
        
        # 1. Descobre os segundos reais pelo Whisper
        start, end = encontrar_timestamps_por_ancoras(transcricao_json_path, ancora_ini, ancora_fim)
        
        logger.info(f"✂️  Processando Corte #{idx}: '{export_id}'")
        logger.info(f"    ⚓ Âncora Inicial: \"{ancora_ini}\"")
        logger.info(f"    ⚓ Âncora Final:   \"{ancora_fim}\"")
        logger.info(f"    🕒 Segundos Cravados: {start:.2f}s até {end:.2f}s")
        
        # 2. Define o arquivo de destino
        output_mp4 = pasta_saida / f"{export_id}.mp4"
        
        # 3. Puxa o trecho direto da fonte (YouTube)
        baixar_trecho_youtube(youtube_id, start, end, output_mp4)
        
        logger.info(f"✨ Corte '{export_id}.mp4' salvo em '{pasta_saida}' pronto para legendas e efeitos!\n")


def main():
    base_dir = Path(__file__).resolve().parent
    yt_id = "2hvx5L2DR2U"
    transcricao_json = base_dir / "data" / "audio_podcasts" / "transcricoes" / "001_2022-10-03_2hvx5L2DR2U_culto_santa_ceia_dia_02_10_2022.json"
    insights_fase3 = base_dir / "data" / "audio_podcasts" / "conteudos_fase3" / "001_2022-10-03_2hvx5L2DR2U_culto_santa_ceia_dia_02_10_2022.insights.json"
    
    payload_json = {}
    
    if insights_fase3.exists():
        logger.info(f"📄 Carregando Timeline Execution Payload real de: {insights_fase3.name}")
        with open(insights_fase3, "r", encoding="utf-8") as f:
            payload_json = json.load(f)
    else:
        logger.info("⚠️ Payload do culto 001 não encontrado localmente. Usando Payload de Exemplo.")
        payload_json = {
            "02_short_form_render_queue": [
                {
                    "export_id": "short_01_nao_ha_ressurreicao_sem_tirar_a_pedra",
                    "extraction_data": {
                        "anchor_start": "Irmão não havia ressurreição Senhor",
                        "anchor_end": "deixa o resto com ele"
                    }
                }
            ]
        }
    
    processar_fase_4(payload_json, transcricao_json, yt_id)


if __name__ == "__main__":
    main()
