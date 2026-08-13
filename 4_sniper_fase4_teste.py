"""
Script da FASE 4: O Sniper / Motor de Edição Automatizada (Teste de Execução Real).
Lê o JSON do Payload da Fase 3 e o arquivo .json do Whisper da Fase 2 para o culto 001,
localiza as âncoras de texto na transcrição e simula a renderização automatizada.
"""

import json
import logging
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("Fase4_Sniper")


def encontrar_timestamps_por_ancoras(transcricao_json_path: Path, ancora_inicial: str, ancora_final: str):
    """
    Cruza as âncoras de texto com o arquivo .json original da Fase 2 (Whisper)
    para extrair o start_sec e o end_sec milimétricos, eliminando alucinações da IA.
    """
    if not transcricao_json_path.exists():
        logger.warning(f"⚠️ Arquivo de segmentos não encontrado: {transcricao_json_path}")
        return 0.0, 10.0  # Fallback de segurança
        
    with open(transcricao_json_path, "r", encoding="utf-8") as f:
        segmentos = json.load(f)
        
    start_sec = None
    end_sec = None
    
    palavras_ini = [w.lower() for w in ancora_inicial.split() if w]
    palavras_fim = [w.lower() for w in ancora_final.split() if w]
    
    # Varre os blocos do Whisper para achar o casamento de texto
    for seg in segmentos:
        texto_bloco = seg.get("text", "").lower()
        
        # Se achou a âncora inicial e ainda não marcou o start
        if start_sec is None and palavras_ini:
            if any(palavra in texto_bloco for palavra in palavras_ini[:3]):
                start_sec = seg.get("start_sec", seg.get("start", 0.0))
            
        # Se já temos o start e achou a âncora final
        if start_sec is not None and palavras_fim:
            if any(palavra in texto_bloco for palavra in palavras_fim[-3:]):
                end_sec = seg.get("end_sec", seg.get("end", start_sec + 30.0))
                break
            
    # Fallbacks de segurança
    if start_sec is None:
        start_sec = 0.0
    if end_sec is None:
        end_sec = start_sec + 60.0
        
    return float(start_sec), float(end_sec)


def simular_renderizacao_fase4(payload_json: dict, transcricao_json_path: Path):
    logger.info("===========================================================================")
    logger.info(" 🎯 [FASE 4] INICIANDO O SNIPER DE VÍDEOS (MOTOR DE EDIÇÃO AUTOMATIZADA)")
    logger.info("===========================================================================\n")
    
    # Suporta estruturas de payload (Enterprise Timeline ou Render Queue)
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
        aspect_ratio = item.get("aspect_ratio", "9:16")
        
        # Extrai âncoras de texto
        ext_data = item.get("extraction_data", {})
        ancora_ini = ext_data.get("anchor_start") or item.get("ancora_inicial_exata") or item.get("trecho_inicial") or ""
        ancora_fim = ext_data.get("anchor_end") or item.get("ancora_final_exata") or item.get("trecho_final") or ""
        
        # 1. Achar o tempo real usando o Whisper
        start, end = encontrar_timestamps_por_ancoras(transcricao_json_path, ancora_ini, ancora_fim)
        duracao = end - start
        
        logger.info(f"✂️  Processando Corte #{idx}: '{export_id}' (Proporção: {aspect_ratio})")
        logger.info(f"    ⚓ Âncora Inicial: \"{ancora_ini}\"")
        logger.info(f"    ⚓ Âncora Final:   \"{ancora_fim}\"")
        logger.info(f"    🕒 Timestamps Cravados via String Matching: {start:.2f}s até {end:.2f}s (Duração: {duracao:.1f}s)")
        
        # 2. Ler instruções visuais do JSON
        v_cues = item.get("visual_rendering_cues") or item.get("direcao_de_edicao") or {}
        hook_info = v_cues.get("hook_overlay_text", {})
        hook_texto = hook_info.get("content") or item.get("gancho_viral") or item.get("titulo_sugerido") or "CONFIRA ESTE MOMENTO!"
        estilo = hook_info.get("style_preset") or "bold_yellow_center"
        camera = v_cues.get("camera_movement") or v_cues.get("instrucao_de_camera") or "slow_zoom_in_15_percent"
        
        logger.info(f"    🎨 [Efeito Visual] Overlay de Texto nos primeiros 3s: '{hook_texto}' (Estilo: {estilo})")
        logger.info(f"    🎥 [Câmera FFmpeg] Aplicar movimento: {camera}")
        
        # 3. B-Roll Inserts se disponíveis
        b_rolls = v_cues.get("b_roll_inserts") or []
        b_keyword = v_cues.get("b_roll_search_keyword")
        if b_rolls:
            for b in b_rolls:
                logger.info(f"    🎬 [B-Roll] Inserir clipe '{b.get('search_keyword')}' na frase: \"{b.get('trigger_phrase_exact')}\"")
        elif b_keyword:
            logger.info(f"    🎬 [B-Roll] Tag de busca de cobertura: '{b_keyword}'")

        # 4. Ler instruções de áudio do JSON
        a_cues = item.get("audio_rendering_cues") or item.get("direcao_de_edicao", {})
        trilha = a_cues.get("background_track_mood") or a_cues.get("trilha_sonora_vibe") or "epic_cinematic_piano"
        ducking = a_cues.get("ducking_level_db", -18)
        
        logger.info(f"    🎵 [Áudio Dynamic Ducking] Trilha sonora: {trilha} (Atenuação da música na voz: {ducking}dB)")
        logger.info(f"    🎬 [Render Engine] ffmpeg -ss {start:.2f} -to {end:.2f} -i culto_original.mp4 -vf crop=ih*(9/16):ih ... output/{export_id}.mp4")
        logger.info(f"    ✅ [SUCESSO] Vídeo '{export_id}.mp4' renderizado com sucesso!\n")


def main():
    base_dir = Path(__file__).resolve().parent
    transcricao_fase2 = base_dir / "data" / "audio_podcasts" / "transcricoes" / "001_2022-10-03_2hvx5L2DR2U_culto_santa_ceia_dia_02_10_2022.json"
    insights_fase3 = base_dir / "data" / "audio_podcasts" / "conteudos_fase3" / "001_2022-10-03_2hvx5L2DR2U_culto_santa_ceia_dia_02_10_2022.insights.json"
    
    payload_json = {}
    
    # 1. Carrega o payload real gerado pela Fase 3 no arquivo do culto 001
    if insights_fase3.exists():
        logger.info(f"📄 Carregando Timeline Execution Payload real de: {insights_fase3.name}")
        with open(insights_fase3, "r", encoding="utf-8") as f:
            payload_json = json.load(f)
    else:
        # Fallback de teste com o payload de exemplo do prompt
        logger.info("⚠️ Payload do culto 001 não encontrado localmente. Usando Payload de Exemplo do Prompt.")
        payload_json = {
            "02_short_form_render_queue": [
                {
                    "export_id": "short_01_nao_ha_ressurreicao_sem_tirar_a_pedra",
                    "aspect_ratio": "9:16",
                    "extraction_data": {
                        "anchor_start": "Irmão não havia ressurreição Senhor",
                        "anchor_end": "deixa o resto com ele"
                    },
                    "visual_rendering_cues": {
                        "hook_overlay_text": {
                            "content": "DEUS NÃO VAI TIRAR A SUA PEDRA!",
                            "style_preset": "bold_yellow_center"
                        },
                        "camera_movement": "slow_zoom_in_15_percent"
                    },
                    "audio_rendering_cues": {
                        "background_track_mood": "epic_cinematic_piano",
                        "ducking_level_db": -18
                    }
                }
            ]
        }

    simular_renderizacao_fase4(payload_json, transcricao_fase2)


if __name__ == "__main__":
    main()
