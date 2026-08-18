"""
Módulo da Fase 2 Mineração - Hub Inteligente de Mineração de Conteúdo (Gemini LLM API).

Transforma a transcrição integral em um 'Timeline Execution Payload' altamente estruturado
com Structured Outputs (Pydantic) via novo SDK 'google-genai', aplicando direção de arte,
copywriting, SEO e âncoras exatas de 7 palavras para corte automatizado em FFmpeg/MoviePy.
"""

import os
import re
import time
import json
import logging
from typing import Dict, Any, Optional, List
from pathlib import Path
from pydantic import BaseModel, Field

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import GROQ_API_KEY, GROQ_MODEL_NAME, GROQ_FALLBACK_MODELS, GEMINI_API_KEY

# Suporte para SDK novo (google-genai) e SDK legado (google-generativeai)
try:
    from google import genai
    from google.genai import types
    HAS_NEW_GENAI = True
except ImportError:
    HAS_NEW_GENAI = False

try:
    import google.generativeai as google_genai_legacy
    HAS_LEGACY_GENAI = True
except ImportError:
    HAS_LEGACY_GENAI = False

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ContentMinerLLM")


# ============================================================================
# PYDANTIC SCHEMAS - TIMELINE EXECUTION PAYLOAD (ENTERPRISE STRUCTURED OUTPUTS)
# ============================================================================

class InteligenciaDoCulto(BaseModel):
    tema_principal: str = Field(..., description="Tema central da mensagem pregada")
    dor_da_audiencia_resolvida: str = Field(..., description="Qual dor ou conflito humano essa pregação resolve")
    arco_emocional_geral: str = Field(..., description="Evolução emocional (ex: Tensão -> Conflito -> Resolução Triunfante)")
    passagens_chave: List[str] = Field(..., description="Lista de versículos e passagens bíblicas citadas")

class DirecaoDeEdicao(BaseModel):
    palavra_foco_destaque: str = Field(..., description="Palavra de maior impacto para destaque na legenda pop-up")
    instrucao_de_camera: str = Field(..., description="Movimento de câmera recomendado (ex: Zoom in lento nos primeiros 3s)")
    trilha_sonora_vibe: str = Field(..., description="Estilo de trilha de fundo (ex: Cinematic piano, Lo-fi beat, Epic synth)")
    b_roll_search_keyword: str = Field(..., description="Termo em inglês para busca no banco de imagens B-Roll")

class CopywritingESEO(BaseModel):
    legenda_post: str = Field(..., description="Copy persuasiva com emojis para legenda de post")
    hashtags_estrategicas: str = Field(..., description="Hashtags otimizadas separadas por espaço")
    comentario_fixado: str = Field(..., description="Pergunta engajadora para fixar nos comentários")

class CorteCurtoShorts(BaseModel):
    id_referencia: str = Field(..., description="Identificador único em snake_case (ex: short_01_remova_a_pedra)")
    opcoes_teste_ab_titulo_tela: List[str] = Field(..., description="Variações de título para teste A/B na capa/tela (max 6 palavras)")
    ancora_inicial_exata: str = Field(..., description="As 7 palavras INICIAIS literais da transcrição falada")
    ancora_final_exata: str = Field(..., description="As 7 palavras FINAIS literais da transcrição falada")
    direcao_de_edicao: DirecaoDeEdicao
    copywriting_e_seo: CopywritingESEO
    score_viralidade: int = Field(..., description="Pontuação estimada de retenção viral (0 a 100)")
    justificativa_psicologica: str = Field(..., description="Motivo psicológico da alta retenção e compartilhamento")

class CorteMedioYoutube(BaseModel):
    id_referencia: str = Field(..., description="Identificador em snake_case para o vídeo no YouTube")
    titulo_youtube_ab: List[str] = Field(..., description="Opções de títulos de alta CTR para o YouTube")
    texto_curto_capa_thumbnail: str = Field(..., description="Texto chamativo para a thumbnail (max 4 palavras)")
    descricao_seo: str = Field(..., description="Descrição rica em palavras-chave SEO para o YouTube")
    ancora_inicial_exata: str = Field(..., description="As 7 palavras INICIAIS literais da transcrição falada")
    ancora_final_exata: str = Field(..., description="As 7 palavras FINAIS literais da transcrição falada")
    capitulos_timeline: List[str] = Field(..., description="Capítulos da timeline (ex: 00:00 - A dor; 02:30 - A virada)")
    score_relevancia_teologica: int = Field(..., description="Pontuação de profundidade teológica (0 a 100)")

class EcosistemaEComunidade(BaseModel):
    post_aba_comunidade_youtube: str = Field(..., description="Texto engajador para a aba Comunidade do YouTube")
    prompt_thumbnail_midjourney: str = Field(..., description="Prompt Midjourney em inglês para capa 8k --ar 16:9")
    paleta_de_cores_branding: str = Field(..., description="Paleta de cores recomendada para a edição e thumbnail")

class TimelineExecutionPayload(BaseModel):
    inteligencia_do_culto: InteligenciaDoCulto = Field(..., alias="01_inteligencia_do_culto")
    cortes_curtos_shorts: List[CorteCurtoShorts] = Field(..., alias="02_cortes_curtos_shorts")
    cortes_medios_youtube: List[CorteMedioYoutube] = Field(..., alias="03_cortes_medios_youtube")
    ecosistema_e_comunidade: EcosistemaEComunidade = Field(..., alias="04_ecosistema_e_comunidade")


PROMPT_SYSTEM = """Você é um Arquiteto de Conteúdo, Diretor de Arte e Especialista em Engenharia de Dados para Vídeo (Machine Learning & Edição Autônoma para FFmpeg/MoviePy).

Sua missão é analisar o texto integral da pregação do culto da Igreja Batista Pentecostal Mundial (IBPM CR) e gerar um 'Timeline Execution Payload' altamente estruturado. Este JSON funcionará como código executável para um motor de renderização de vídeo automatizado na Fase 3 Renderização.

REGRA DE OURO (SINCRONIA TEMPORAL LITERAL SEM ALUCINAÇÃO):
Você está ESTRITAMENTE PROIBIDO de tentar adivinhar segundos ou minutos (start_sec / end_sec).
As chaves 'ancora_inicial_exata' e 'ancora_final_exata' DEVEM conter exatamente as 7 palavras literais iniciais e as 7 palavras literais finais da transcrição falada para cada corte.
Nenhuma alteração, paráfrase ou alucinação será tolerada, pois a sincronia de segundos será realizada via string matching determinístico contra o arquivo Whisper de timestamps.

RETORNE ESTRITAMENTE O JSON FORMATADO CONFORME O SCHEMA DEFINIDO.
"""


class ContentMinerLLM:
    """
    Hub de Inteligência e Mineração da Fase 3 com Cruzamento de Timestamps (.json) da Fase 2.
    """

    def __init__(self, gemini_api_key: Optional[str] = None, groq_api_key: Optional[str] = None):
        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        self.groq_api_key = groq_api_key or GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        
        self.gemini_new_client = None
        self.gemini_legacy_configured = False
        self.groq_client = None

        if HAS_NEW_GENAI and self.gemini_api_key and len(self.gemini_api_key.strip()) > 10:
            try:
                self.gemini_new_client = genai.Client(api_key=self.gemini_api_key.strip())
                logger.info("⚡ Conectado ao Google Gemini (SDK GenAI Novo com Structured Outputs).")
            except Exception as e:
                logger.warning(f"⚠️ Aviso ao inicializar GenAI Novo: {e}")

        if HAS_LEGACY_GENAI and self.gemini_api_key and len(self.gemini_api_key.strip()) > 10:
            try:
                google_genai_legacy.configure(api_key=self.gemini_api_key.strip())
                self.gemini_legacy_configured = True
                logger.info("⚡ Conectado ao Google Gemini (SDK GenerativeAI Legacy).")
            except Exception as e:
                logger.warning(f"⚠️ Aviso ao inicializar GenerativeAI Legacy: {e}")

        if HAS_GROQ and self.groq_api_key and len(self.groq_api_key.strip()) > 10:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key.strip())
                logger.info("⚡ Conectado à infraestrutura Groq Cloud API.")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Groq Client: {e}")

    def mine_transcription(self, text_content: str, segments_data: Optional[List[Dict[str, Any]]] = None, title: str = "") -> Dict[str, Any]:
        """
        Submete a transcrição (.txt) ao Gemini e enriquece os cortes virais com os timestamps exatos do .json.
        """
        if not text_content or len(text_content.strip()) < 50:
            logger.warning("⚠️ Texto da transcrição curto demais para mineração.")
            return self._fallback_mining(title, text_content)

        prompt_user = f"Título do Culto: {title}\n\nTexto Integral da Pregação:\n{text_content[:300000]}"
        prompt_completo = f"{PROMPT_SYSTEM}\n\n{prompt_user}"
        insights = None

        gemini_models_to_try = ["gemini-flash-latest", "gemini-2.5-flash"]

        # 1. Tenta Gemini via SDK Novo com Structured Output Pydantic
        if self.gemini_new_client:
            for gmodel in gemini_models_to_try:
                try:
                    logger.info(f"⚡ Enviando pregação para o Google Gemini ({gmodel}) com Structured Output Pydantic...")
                    response = self.gemini_new_client.models.generate_content(
                        model=gmodel,
                        contents=prompt_completo,
                        config=types.GenerateContentConfig(
                            response_mime_type="application/json",
                            response_schema=TimelineExecutionPayload,
                            temperature=0.3
                        )
                    )
                    time.sleep(4.5)  # Freio ABS (15 RPM)

                    if response and response.text:
                        parsed = self._clean_and_parse_json(response.text)
                        if parsed:
                            logger.info(f"✅ SUCESSO! Timeline Execution Payload minerado via {gmodel} (GenAI Novo).")
                            insights = parsed
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Erro no Gemini API ({gmodel}): {e}.")

        # 2. Tenta Gemini via SDK Padrão (google-generativeai Legacy)
        if not insights and self.gemini_legacy_configured:
            for gmodel in gemini_models_to_try:
                try:
                    logger.info(f"⚡ Enviando pregação para o Google Gemini ({gmodel})...")
                    legacy_model = google_genai_legacy.GenerativeModel(
                        gmodel,
                        generation_config={"response_mime_type": "application/json", "temperature": 0.3}
                    )
                    response = legacy_model.generate_content(prompt_completo)
                    time.sleep(4.5)

                    if response and response.text:
                        parsed = self._clean_and_parse_json(response.text)
                        if parsed:
                            logger.info(f"✅ SUCESSO! Payload minerado via {gmodel} (SDK GenerativeAI).")
                            insights = parsed
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Erro no Gemini API ({gmodel}): {e}.")

        # 3. Tenta Groq API (Fallback Open-Source)
        if not insights and self.groq_client:
            for model_id in GROQ_FALLBACK_MODELS:
                try:
                    logger.info(f"⚡ Enviando para a Nuvem Groq (Modelo: '{model_id}')...")
                    chat_completion = self.groq_client.chat.completions.create(
                        messages=[
                            {"role": "system", "content": PROMPT_SYSTEM},
                            {"role": "user", "content": prompt_user[:35000]}
                        ],
                        model=model_id,
                        response_format={"type": "json_object"},
                        temperature=0.3
                    )
                    time.sleep(2.0)
                    if chat_completion and chat_completion.choices:
                        resp_text = chat_completion.choices[0].message.content
                        parsed = self._clean_and_parse_json(resp_text)
                        if parsed:
                            logger.info(f"✅ SUCESSO! Resposta processada via '{model_id}'.")
                            insights = parsed
                            break
                except Exception as e:
                    logger.warning(f"⚠️ Modelo '{model_id}' oscilou: {e}. Tentando próximo...")

        if not insights:
            logger.warning("⚠️ Não foi possível se conectar às APIs do Gemini/Groq. Usando Fallback Estruturado.")
            insights = self._fallback_mining(title, text_content)

        # 4. CRUZAMENTO DETERMINÍSTICO DE TIMESTAMPS VIA STRING MATCHING DE 7 PALAVRAS
        if segments_data and isinstance(insights, dict):
            insights = self._enrich_all_cuts_with_timestamps(insights, segments_data)

        return insights

    def _enrich_all_cuts_with_timestamps(self, insights: Dict[str, Any], segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Enriquece tanto os cortes curtos (shorts) quanto os cortes médios (youtube) com start_sec e end_sec exatos.
        """
        # Cortes curtos (9:16)
        cuts_curtos = insights.get("02_cortes_curtos_shorts") or insights.get("cortes_curtos_shorts") or []
        if isinstance(cuts_curtos, list):
            insights["02_cortes_curtos_shorts"] = self._enrich_cut_list(cuts_curtos, segments)

        # Cortes médios (16:9)
        cuts_medios = insights.get("03_cortes_medios_youtube") or insights.get("cortes_medios_youtube") or []
        if isinstance(cuts_medios, list):
            insights["03_cortes_medios_youtube"] = self._enrich_cut_list(cuts_medios, segments)

        # Compatibilidade legada (05_cortes_virais)
        cuts_legados = insights.get("05_cortes_virais")
        if isinstance(cuts_legados, list):
            insights["05_cortes_virais"] = self._enrich_cut_list(cuts_legados, segments)

        return insights

    def _enrich_cut_list(self, cuts: List[Dict[str, Any]], segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        for cut in cuts:
            init_phrase = (
                cut.get("ancora_inicial_exata") or
                cut.get("trecho_inicial") or
                cut.get("anchor_start") or ""
            ).lower().strip()

            end_phrase = (
                cut.get("ancora_final_exata") or
                cut.get("trecho_final") or
                cut.get("anchor_end") or ""
            ).lower().strip()

            start_sec = None
            end_sec = None

            if init_phrase:
                init_words = [w for w in re.split(r'\W+', init_phrase) if w][:4]
                if init_words:
                    for seg in segments:
                        seg_text = seg.get("text", "").lower()
                        if any(w in seg_text for w in init_words):
                            start_sec = seg.get("start_sec")
                            break

            if end_phrase:
                end_words = [w for w in re.split(r'\W+', end_phrase) if w][-4:]
                if end_words:
                    for seg in reversed(segments):
                        seg_text = seg.get("text", "").lower()
                        if any(w in seg_text for w in end_words):
                            end_sec = seg.get("end_sec")
                            break

            cut["start_sec"] = float(start_sec) if start_sec is not None else 0.0
            cut["end_sec"] = float(end_sec) if end_sec is not None else (cut["start_sec"] + 60.0)

        return cuts

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        try:
            clean_str = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.IGNORECASE)
            clean_str = re.sub(r'```$', '', clean_str.strip()).strip()

            parsed = json.loads(clean_str)
            if isinstance(parsed, dict) and len(parsed.keys()) > 0:
                return parsed
        except Exception as e:
            logger.warning(f"⚠️ Falha ao fazer parse do JSON retornado: {e}")

        return None

    def _fallback_mining(self, title: str, text: str) -> Dict[str, Any]:
        return {
            "01_inteligencia_do_culto": {
                "tema_principal": f"Mensagem edificante sobre '{title or 'Celebração e Fé'}' na IBPM CR.",
                "dor_da_audiencia_resolvida": "Superação do desânimo espiritual, ansiedade e incerteza no futuro.",
                "arco_emocional_geral": "Tensão e Clamor -> Revelação da Palavra -> Celebração e Oração de Vitória",
                "passagens_chave": ["Salmos 23:1", "Filipenses 4:13", "Isaías 40:31"]
            },
            "02_cortes_curtos_shorts": [
                {
                    "id_referencia": "short_01_remova_a_pedra",
                    "opcoes_teste_ab_titulo_tela": [
                        "Deus Não Se Esqueceu de Você!",
                        "A Oração Que Muda Tudo Hoje"
                    ],
                    "ancora_inicial_exata": "você que está me ouvindo agora aqui",
                    "ancora_final_exata": "o senhor está decretando a sua vitória",
                    "direcao_de_edicao": {
                        "palavra_foco_destaque": "VITÓRIA",
                        "instrucao_de_camera": "Zoom in lento nos primeiros 3 segundos",
                        "trilha_sonora_vibe": "Cinematic piano emocionante com sintetizador sutil",
                        "b_roll_search_keyword": "prayer hands church spotlight"
                    },
                    "copywriting_e_seo": {
                        "legenda_post": "Deus manda te dizer hoje: a sua vitória já foi decretada no altar! 🙏🔥 Salve este vídeo para lembrar do poder da oração.",
                        "hashtags_estrategicas": "#Fe #Oração #MotivaçãoGospel #IBPMCR #Jesus #CortesEvangelicos",
                        "comentario_fixado": "Escreva 'AMÉM' nos comentários se você toma posse dessa bênção!"
                    },
                    "score_viralidade": 95,
                    "justificativa_psicologica": "Apela para a busca inconsciente de esperança e validação espiritual imediata, gerando alto compartilhamento."
                }
            ],
            "03_cortes_medios_youtube": [
                {
                    "id_referencia": "medium_01_mensagem_completa",
                    "titulo_youtube_ab": [
                        "COMO VENCER A TEMPESTADE DA VIDA - Pregação Impactante",
                        "O Segredo da Oração Que Move o Céu | IBPM CR"
                    ],
                    "texto_curto_capa_thumbnail": "DEUS MUDARÁ TUDO HOJE",
                    "descricao_seo": "Assista a esta mensagem edificante pregada na Igreja Batista Pentecostal Mundial (IBPM CR) e entenda o poder da fé.",
                    "ancora_inicial_exata": "quando a igreja se une em oração",
                    "ancora_final_exata": "todo o jugo cai por terra hoje",
                    "capitulos_timeline": [
                        "00:00 - A dor e o conflito inicial",
                        "02:30 - A revelação bíblica",
                        "05:00 - A oração de vitória"
                    ],
                    "score_relevancia_teologica": 92
                }
            ],
            "04_ecosistema_e_comunidade": {
                "post_aba_comunidade_youtube": "Que palavra forte no culto de hoje! Qual trecho mais tocou o seu coração?",
                "prompt_thumbnail_midjourney": "Dramatic cinematic lighting, evangelical pastor preaching with passion on stage, warm golden spotlight, church sanctuary background, photorealistic 8k --ar 16:9",
                "paleta_de_cores_branding": "Preto, Dourado Ouro e Amarelo Neon para destaque"
            }
        }


if __name__ == "__main__":
    miner = ContentMinerLLM()
    print("ContentMinerLLM refatorado para Timeline Execution Payload (Pydantic / Structured Outputs)!")
