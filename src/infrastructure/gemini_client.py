"""
Cliente de Mineração Teológica com Google Gemini API - IBPM CR Automation System.

Utiliza o SDK novo 'google-genai' com Pydantic V2 Structured Outputs e File API para realizar a
mineração cognitiva de pregações diretamente de arquivos MP3/M4A locais ou de textos transcritos.
"""

import time
from pathlib import Path
from typing import Dict, Any, Optional

from google import genai
from google.genai import types

from src.core.config import settings
from src.core.logger import get_logger
from src.domain.schemas import SermonMiningResponse

logger = get_logger("TheologyMinerClient")


SYSTEM_PROMPT_PENTECOSTAL = """Você é o motor de processamento cognitivo do IBPM CR AUTOMATION SYSTEM, especializado na análise exegética e mineração de conteúdo audiovisual eclesiástico pentecostal.

Sua tarefa é analisar a transcrição ou o áudio bruto de um culto, identificar os momentos de maior impacto homilético, teológico ou emocional, e retornar uma estrutura JSON validada contendo os cortes selecionados para os formatos Short-Form (9:16) e Mid-Form (16:9).

DIRETRIZES DE PROCESSAMENTO:
1. PRESERVAÇÃO TEOLÓGICA: Mantenha a fidelidade absoluta ao sentido exegético original do pregador. Não reescreva, comente ou altere a doutrina expressa no texto.
2. IDENTIFICAÇÃO DE ÂNCORAS LITERAIS: Para cada corte identificado, você DEVE extrair exatamente 7 (sete) palavras consecutivas verbatim para a "start_anchor_7_words" (início) e exatamente 7 (sete) palavras consecutivas verbatim para a "end_anchor_7_words" (fim).
3. PONTUAÇÃO E ORTOGRAFIA DAS ÂNCORAS: As âncoras de 7 palavras devem ser uma cópia IDÊNTICA e literal do áudio/texto fornecido, para permitir a busca por casamento exato no alinhamento determinístico downstream.
4. MÉTRICAS DE CORTE:
   - Short-Form (9:16): Duração ideal entre 30 e 59 segundos. Foco em frases de impacto, ilustrações diretas e declarações de fé.
   - Mid-Form (16:9): Duração ideal entre 3 e 12 minutos. Foco em explicações teológicas completas, exegese de passagens bíblicas ou reflexões profundas.

RETORNE EXCLUSIVAMENTE O PAYLOAD STRUCTURAL CONFORME O SCHEMA DEFINIDO.
"""


class TheologyMinerClient:
    """
    Cliente wrapper para mineração teológica via Gemini 1.5 Flash usando Structured Outputs e File API.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY or settings.GOOGLE_API_KEY
        if not self.api_key or len(self.api_key.strip()) < 10:
            raise ValueError("Chave de API do Gemini não configurada no ambiente (GEMINI_API_KEY).")

        self.client = genai.Client(api_key=self.api_key.strip())
        logger.info("Cliente TheologyMinerClient (Gemini GenAI) inicializado com sucesso.")

    def analyze_transcript(
        self,
        transcript_text: str,
        source_video_id: str = "IBPM_CULTO",
        model_name: Optional[str] = None,
        job_id: str = "job_gemini_mining"
    ) -> SermonMiningResponse:
        """
        Submete a transcrição contínua do culto ao Gemini e retorna a estrutura Pydantic SermonMiningResponse.
        """
        if not transcript_text or len(transcript_text.strip()) < 50:
            raise ValueError("Texto da transcrição é insuficiente para análise teológica.")

        target_model = model_name or settings.GOOGLE_GEMINI_MODEL or "gemini-flash-latest"

        prompt_user = f"ID do Vídeo de Origem: {source_video_id}\n\nTranscrição Bruta do Culto:\n{transcript_text[:300000]}"
        prompt_completo = f"{SYSTEM_PROMPT_PENTECOSTAL}\n\n{prompt_user}"

        logger.info(
            "Enviando transcrição para mineração no Gemini API",
            job_id=job_id,
            model=target_model,
            text_length=len(transcript_text)
        )

        try:
            response = self.client.models.generate_content(
                model=target_model,
                contents=prompt_completo,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SermonMiningResponse,
                    temperature=0.3
                )
            )

            time.sleep(4.5)

            if not response or not response.text:
                raise RuntimeError("Resposta vazia retornada pela API do Gemini.")

            if hasattr(response, "parsed") and response.parsed:
                parsed_response: SermonMiningResponse = response.parsed
                parsed_response.job_id = job_id
                parsed_response.source_video_id = source_video_id
                return parsed_response

            parsed_json = SermonMiningResponse.model_validate_json(response.text)
            parsed_json.job_id = job_id
            parsed_json.source_video_id = source_video_id
            return parsed_json

        except Exception as e:
            logger.error("Falha na mineração teológica do Gemini", job_id=job_id, error=str(e))
            raise RuntimeError(f"Erro na API do Gemini: {str(e)}")

    def analyze_audio_file(
        self,
        audio_file_path: Path,
        source_video_id: str = "IBPM_CULTO",
        model_name: Optional[str] = None,
        job_id: str = "job_audio_gemini"
    ) -> SermonMiningResponse:
        """
        Rota Nativa do Gemini 1.5 via File API com Polling de Ativação (ACTIVE):
        Faz upload do MP3 local para a File API do Google, aguarda o status transitar para ACTIVE
        e realiza a transcrição + mineração teológica em um único passo.
        """
        if not audio_file_path.exists():
            raise FileNotFoundError(f"Arquivo de áudio local não encontrado: {audio_file_path}")

        target_model = model_name or settings.GOOGLE_GEMINI_MODEL or "gemini-flash-latest"

        logger.info(
            "📤 Enviando áudio MP3 local para a File API do Gemini",
            job_id=job_id,
            audio_file=audio_file_path.name,
            size_mb=round(audio_file_path.stat().st_size / (1024 * 1024), 2)
        )

        uploaded_file = None
        try:
            # 1. Upload do MP3 para a Gemini File API
            uploaded_file = self.client.files.upload(file=str(audio_file_path))
            logger.info("✅ Upload concluído na File API. Aguardando ativação (ACTIVE)...", job_id=job_id, file_ref=uploaded_file.name)

            # 2. Polling Resiliente de Ativação do Arquivo no Google
            start_poll = time.time()
            while True:
                state_str = str(getattr(uploaded_file, "state", "")).upper()
                
                # Se o estado contiver ACTIVE e não estiver em PROCESSING
                if "ACTIVE" in state_str and "PROCESSING" not in state_str:
                    logger.info("🟢 Arquivo de áudio ativado nos servidores do Google (ACTIVE)", job_id=job_id)
                    break
                
                if "FAILED" in state_str or "ERROR" in state_str:
                    raise RuntimeError(f"O arquivo de áudio falhou na indexação do Google: {state_str}")

                if (time.time() - start_poll) > 600:
                    raise TimeoutError("Tempo limite (10 min) excedido aguardando indexação do áudio na File API.")

                logger.info(f"⏳ Indexando áudio nos servidores do Google (Estado: {state_str}). Aguardando 5s...", job_id=job_id)
                time.sleep(5)
                uploaded_file = self.client.files.get(name=uploaded_file.name)

            prompt_user = (
                f"{SYSTEM_PROMPT_PENTECOSTAL}\n\n"
                f"ID do Vídeo de Origem: {source_video_id}\n\n"
                f"Instrução: Ouça atentamente este áudio do culto da Igreja Batista Pentecostal Mundial (IBPM CR). "
                f"Faça a transcrição analítica completa e extraia todos os cortes virais nos formatos Short-Form (9:16) "
                f"e Mid-Form (16:9) com âncoras exatas de 7 palavras consecutivas."
            )

            # 3. Inferência Multimodal Nativa com Pydantic Structured Output
            logger.info("🧠 Disparando mineração multimodal no Gemini 1.5 Flash", job_id=job_id, model=target_model)
            response = self.client.models.generate_content(
                model=target_model,
                contents=[uploaded_file, prompt_user],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=SermonMiningResponse,
                    temperature=0.3
                )
            )

            time.sleep(4.5)

            if not response or not response.text:
                raise RuntimeError("Resposta vazia retornada pela API do Gemini no processamento de áudio.")

            parsed_response = None
            if hasattr(response, "parsed") and response.parsed:
                parsed_response = response.parsed
            else:
                parsed_response = SermonMiningResponse.model_validate_json(response.text)

            parsed_response.job_id = job_id
            parsed_response.source_video_id = source_video_id

            logger.info(
                "🎉 Mineração e Transcrição Nativa via Áudio concluídas com sucesso!",
                job_id=job_id,
                short_cuts=len(parsed_response.short_form_cuts),
                mid_cuts=len(parsed_response.mid_form_cuts)
            )
            return parsed_response

        except Exception as e:
            logger.error("Falha no processamento de áudio via Gemini File API", job_id=job_id, error=str(e))
            raise RuntimeError(f"Erro no processamento de áudio do Gemini: {str(e)}")
        finally:
            # 4. Limpeza automática do arquivo temporário na File API
            if uploaded_file and hasattr(uploaded_file, "name"):
                try:
                    self.client.files.delete(name=uploaded_file.name)
                    logger.info("🗑️ Arquivo temporário removido da File API do Gemini", file_ref=uploaded_file.name)
                except Exception:
                    pass
