"""
🤖 BOT DE AUTOMAÇÃO TOTAL DE ALTA ACCURACY - IBPM CR AUTOMATION SYSTEM

Monitora continuamente a pasta de áudios (local ou no Google Drive),
transcreve cada áudio com modelo TOPO DE LINHA de acurácia (Faster-Whisper Large-v3 / Medium com beam_size=5)
e dispara a mineração inteligente via Groq LLM (Llama 3.3 70B),
atualizando o banco SQLite e a pasta do Google Drive de forma 100% autônoma!
"""

import sys
import os
import time
import json
import logging
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.append(str(Path(__file__).resolve().parent))

from config.settings import AUDIO_DIR, INSIGHTS_DIR, DB_PATH, GROQ_API_KEY
from src.core.state_manager import MasterPlanManager
from src.discovery.transcriber_batch import BatchTranscriber
from src.discovery.content_miner_llm import ContentMinerLLM

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("BotTranscritorAuto")


def print_banner():
    banner = f"""
===========================================================================
 🤖 BOT DE AUTOMAÇÃO DE ALTA PRECISÃO - IBPM CR (LARGE-V3 + GROQ LLM)
   Modo: 100% Autônomo e Silencioso (Zero Intervenção Humana)
   Pasta de Monitoramento: {AUDIO_DIR}
   Modelo de Transcrição: Faster-Whisper Large-v3 / Medium (Full Accuracy)
   Modelo de Inteligência: Groq Cloud API (Llama 3.3 70B Open-Source)
===========================================================================
    """
    print(banner)


class IBPMAutomationBot:
    def __init__(self, model_size: str = "large-v3"):
        self.state_mgr = MasterPlanManager()
        self.transcriber = BatchTranscriber(model_size=model_size)
        self.miner = ContentMinerLLM(groq_api_key=GROQ_API_KEY)

    def run_continuous_loop(self, poll_interval_sec: int = 15):
        logger.info("🤖 Bot de Automação iniciado! Monitorando fila de cultos continuamente...\n")
        
        while True:
            try:
                processed_transcription = self._step_transcribe_next()
                processed_mining = self._step_mine_next()

                if not processed_transcription and not processed_mining:
                    time.sleep(poll_interval_sec)

            except KeyboardInterrupt:
                logger.info("\n🛑 Bot de Automação encerrado manualmente.")
                break
            except Exception as e:
                logger.warning(f"⚠️ Ocorreu um erro no ciclo do Bot: {e}. Reiniciando em 10 segundos...")
                time.sleep(10)

    def _step_transcribe_next(self) -> bool:
        all_videos = self.state_mgr.get_all_videos_chronological()
        
        target = None
        for v in all_videos:
            v_id = v["video_id"]
            audio_path = self.transcriber._find_audio_file_on_disk(v_id)
            if not audio_path:
                continue

            base_path = os.path.splitext(audio_path)[0]
            txt_path = base_path + ".txt"

            already_done = (
                self.state_mgr.is_transcribed(v_id) and
                os.path.exists(txt_path) and os.path.getsize(txt_path) > 100
            )

            if not already_done:
                target = (v, audio_path)
                break

        if not target:
            return False

        item, audio_path = target
        v_id = item["video_id"]
        idx = item.get("indice_sequencial", 1)

        logger.info(f"\n🎙️ [BOT] Transcrevendo Culto [{idx:03d}] (ID: {v_id}) em Alta Precisão...")
        res = self.transcriber.transcribe_single_audio(audio_path, video_id=v_id, item_meta=item)

        if res and res.get("texto_completo"):
            logger.info(f"✅ [BOT] Transcrição integral do Culto [{idx:03d}] concluída com sucesso! (.txt e .json gerados)")
            return True

        return False

    def _step_mine_next(self) -> bool:
        all_videos = self.state_mgr.get_all_videos_chronological()
        
        target = None
        for v in all_videos:
            v_id = v["video_id"]
            idx = v.get("indice_sequencial", 1)

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

            already_mined = (
                out_json_path.exists() and
                out_json_path.stat().st_size > 100 and
                self.state_mgr.is_insight_processed(v_id)
            )

            if not already_mined:
                target = (v, txt_file, out_json_path)
                break

        if not target:
            return False

        item, txt_path, out_json_path = target
        v_id = item["video_id"]
        idx = item.get("indice_sequencial", 1)
        title = item.get("titulo_original", "")

        if txt_path.startswith("sqlite_video_"):
            text_content = item.get("texto_transcrito", "")
        else:
            try:
                with open(txt_path, "r", encoding="utf-8") as f:
                    text_content = f.read()
            except Exception as e:
                logger.warning(f"⚠️ [BOT] Erro ao ler arquivo .txt {txt_path}: {e}")
                return False

        logger.info(f"🧠 [BOT] Enviando Culto [{idx:03d}] (ID: {v_id}) para o Groq LLM (Llama 3.3 70B)...")
        insights_dict = self.miner.mine_transcription(text_content=text_content, title=title)

        if insights_dict:
            raw_json_str = json.dumps(insights_dict, ensure_ascii=False, indent=2)

            with open(out_json_path, "w", encoding="utf-8") as f:
                f.write(raw_json_str)

            self.state_mgr.save_insights_fase3(
                video_id=v_id,
                idx=idx,
                title=title,
                insights_dict=insights_dict,
                raw_json=raw_json_str
            )
            logger.info(f"✨ [BOT] Insights do Culto [{idx:03d}] salvos no disco e no SQLite!")
            return True

        return False


def main():
    print_banner()
    bot = IBPMAutomationBot(model_size="large-v3")
    bot.run_continuous_loop(poll_interval_sec=10)


if __name__ == "__main__":
    main()
