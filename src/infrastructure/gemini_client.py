"""
Cliente de Mineração Teológica com Google Gemini API - IBPM CR Automation System.

Utiliza o SDK novo 'google-genai' com Pydantic V2 Structured Outputs para realizar a
mineração cognitiva de pregações, isolando Unidades de Pensamento Completo (UPC),
métricas de retenção visual e âncoras verbais exatas de 7 palavras.
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

Sua tarefa é analisar a transcrição bruta de um culto, identificar os momentos de maior impacto homilético, teológico ou emocional, e retornar uma estrutura JSON validada contendo os cortes selecionados para os formatos Short-Form (9:16) e Mid-Form (16:9).

DIRETRIZES DE PROCESSAMENTO:
1. PRESERVAÇÃO TEOLÓGICA: Mantenha a fidelidade absoluta ao sentido exegético original do pregador. Não reescreva, comente ou altere a doutrina expressa no texto.
2. IDENTIFICAÇÃO DE ÂNCORAS LITERAIS: Para cada corte identificado, você DEVE extrair exatamente 7 (sete) palavras consecutivas verbatim da transcrição bruta para a "start_anchor_7_words" (início) e exatamente 7 (sete) palavras consecutivas verbatim para a "end_anchor_7_words" (fim).
3. PONTUAÇÃO E ORTOGRAFIA DAS ÂNCORAS: As âncoras de 7 palavras devem ser uma cópia IDÊNTICA e literal do texto bruto fornecido, para permitir a busca por casamento exato no alinhamento determinístico downstream.
4. MÉTRICAS DE CORTE:
   - Short-Form (9:16): Duração ideal entre 30 e 59 segundos. Foco em frases de impacto, ilustrações diretas e declarações de fé.
   - Mid-Form (16:9): Duração ideal entre 3 e 12 minutos. Foco em explicações teológicas completas, exegese de passagens bíblicas ou reflexões profundas.

RETORNE EXCLUSIVAMENTE O PAYLOAD STRUCTURAL CONFORME O SCHEMA DEFINIDO.
"""


class TheologyMinerClient:
    """
    Cliente wrapper para mineração teológica via Gemini 1.5 Flash usando Structured Outputs.
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

            # Freio ABS para respeitar os limites de requisição por minuto (RPM)
            time.sleep(4.5)

            if not response or not response.text:
                raise RuntimeError("Resposta vazia retornada pela API do Gemini.")

            # O SDK novo faz o parse direto para a classe Pydantic fornecida no response_schema
            if hasattr(response, "parsed") and response.parsed:
                parsed_response: SermonMiningResponse = response.parsed
                parsed_response.job_id = job_id
                parsed_response.source_video_id = source_video_id
                
                logger.info(
                    "Mineração teológica concluída com sucesso via SDK GenAI",
                    job_id=job_id,
                    short_cuts=len(parsed_response.short_form_cuts),
                    mid_cuts=len(parsed_response.mid_form_cuts)
                )
                return parsed_response

            # Parsing manual de fallback em caso de retorno string pura JSON
            parsed_json = SermonMiningResponse.model_validate_json(response.text)
            parsed_json.job_id = job_id
            parsed_json.source_video_id = source_video_id
            
            logger.info("Mineração teológica concluída com sucesso (fallback parse)", job_id=job_id)
            return parsed_json

        except Exception as e:
            logger.error("Falha na mineração teológica do Gemini", job_id=job_id, error=str(e))
            raise RuntimeError(f"Erro na API do Gemini: {str(e)}")
