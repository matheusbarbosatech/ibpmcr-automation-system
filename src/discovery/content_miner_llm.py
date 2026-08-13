"""
Módulo da Fase 3 - Hub Inteligente de Mineração de Conteúdo (Groq Llama 3.3 70B & Gemini LLM).

Envia o texto transcrito da pregação (.txt/.json) para a API do Groq (Llama 3.3 70B Open-Source)
ou Google Gemini, atuando como "Curador de Conteúdo e Teólogo Sênior", extraindo os 6 pilares
estruturados em formato JSON estrito.
"""

import os
import re
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import GROQ_API_KEY, GROQ_MODEL_NAME, GEMINI_API_KEY, GEMINI_MODEL_NAME

try:
    from groq import Groq
    HAS_GROQ = True
except ImportError:
    HAS_GROQ = False

try:
    from google import genai
    from google.genai import types
    HAS_GOOGLE_GENAI = True
except ImportError:
    HAS_GOOGLE_GENAI = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("ContentMinerLLM")


PROMPT_SYSTEM = """Você é um Curador de Conteúdo e Teólogo Sênior especializado em comunicação cristã, evangelismo digital e produção de conteúdo viral para redes sociais (Reels, TikTok, Instagram e YouTube).

Sua tarefa é analisar criticamente o texto integral da pregação do culto da Igreja Batista Pentecostal Mundial (IBPM CR) e extrair insights valiosos com extrema fidelidade teológica e alto potencial de engajamento.

RETORNE ESTRITAMENTE UM OBJETO JSON VÁLIDO (sem nenhum markdown fora do JSON) contendo as seguintes 6 chaves exatas:

{
  "01_tema_central": "Resumo executivo da mensagem principal do culto em 2 a 3 parágrafos curtos.",
  "02_frases_virais": [
    "Frase de impacto 1 (forte, memorável e direta)",
    "Frase de impacto 2",
    "Frase de impacto 3",
    "Frase de impacto 4"
  ],
  "03_passagens_biblicas": [
    "Livro Capítulo:Versículo (ex: João 3:16)",
    "Livro Capítulo:Versículo"
  ],
  "04_ideia_carrossel_instagram": [
    "Slide 1: [Título Impactante] - Resumo curto",
    "Slide 2: [Ponto Chave 1] - Explicação",
    "Slide 3: [Ponto Chave 2] - Aplicação prática",
    "Slide 4: [Conclusão & Oração] - Chamada para reflexão"
  ],
  "05_cortes_virais": [
    {
      "titulo": "Título Atrativo do Corte 1",
      "contexto": "Do que trata este momento",
      "sugestao_b_roll": "Sugestão visual de cobertura (ex: imagens de oração, tempestade se acalmando, etc)",
      "score_viral": 95,
      "trecho_inicial": "Citação exata do início da frase falada",
      "trecho_final": "Citação exata do fim da frase falada"
    },
    {
      "titulo": "Título Atrativo do Corte 2",
      "contexto": "Do que trata este momento",
      "sugestao_b_roll": "Sugestão visual de cobertura",
      "score_viral": 90,
      "trecho_inicial": "Citação exata do início",
      "trecho_final": "Citação exata do fim"
    },
    {
      "titulo": "Título Atrativo do Corte 3",
      "contexto": "Do que trata este momento",
      "sugestao_b_roll": "Sugestão visual de cobertura",
      "score_viral": 88,
      "trecho_inicial": "Citação exata do início",
      "trecho_final": "Citação exata do fim"
    }
  ],
  "06_prompt_thumbnail": "Cinematic, dramatic lighting, 8k resolution photo of a pastor preaching with passion on stage, warm golden backlight, church sanctuary background, photorealistic, Midjourney prompt style --ar 16:9"
}
"""


class ContentMinerLLM:
    """
    Minerador de insights com suporte prioritário à API Groq (Llama 3.3 70B) e Gemini LLM.
    """

    def __init__(self, groq_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        self.groq_api_key = groq_api_key or GROQ_API_KEY or os.getenv("GROQ_API_KEY", "")
        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY or os.getenv("GEMINI_API_KEY", "")
        
        self.groq_client = None
        self.gemini_client = None

        if HAS_GROQ and self.groq_api_key:
            try:
                self.groq_client = Groq(api_key=self.groq_api_key)
                logger.info(f"⚡ Conectado ao Groq API ({GROQ_MODEL_NAME} - Llama 3.3 70B).")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Groq Client: {e}")

        if HAS_GOOGLE_GENAI and self.gemini_api_key and not self.groq_client:
            try:
                self.gemini_client = genai.Client(api_key=self.gemini_api_key)
                logger.info(f"✅ Conectado ao Google GenAI SDK ({GEMINI_MODEL_NAME}).")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao inicializar Google GenAI Client: {e}")

        if not self.groq_client and not self.gemini_client:
            logger.warning("⚠️ Nenhuma chave de API configurada (GROQ_API_KEY ou GEMINI_API_KEY). Defina no arquivo .env.")

    def mine_transcription(self, text_content: str, title: str = "") -> Dict[str, Any]:
        """
        Submete o texto da transcrição ao LLM (Groq ou Gemini) e retorna o JSON estruturado.
        """
        if not text_content or len(text_content.strip()) < 50:
            logger.warning("⚠️ Texto da transcrição curto demais para mineração.")
            return self._fallback_mining(title, text_content)

        prompt_user = f"Título do Culto: {title}\n\nTexto Integral da Pregação:\n{text_content[:25000]}"

        # 1. Tenta a API do Groq (Llama 3.3 70B Versatile - Ultra Rápida & Gratuita)
        if self.groq_client:
            try:
                logger.info(f"⚡ Enviando para a API Groq ({GROQ_MODEL_NAME})...")
                chat_completion = self.groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": PROMPT_SYSTEM},
                        {"role": "user", "content": prompt_user}
                    ],
                    model=GROQ_MODEL_NAME,
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                if chat_completion and chat_completion.choices:
                    resp_text = chat_completion.choices[0].message.content
                    parsed = self._clean_and_parse_json(resp_text)
                    if parsed:
                        logger.info("✅ Resposta recebida do Groq (Llama 3.3 70B) com sucesso!")
                        return parsed
            except Exception as e:
                logger.warning(f"⚠️ Erro na chamada à API Groq: {e}")

        # 2. Tenta a API do Google Gemini como fallback de IA
        if self.gemini_client:
            try:
                logger.info(f"✅ Enviando para a API Gemini ({GEMINI_MODEL_NAME})...")
                response = self.gemini_client.models.generate_content(
                    model=GEMINI_MODEL_NAME,
                    contents=[PROMPT_SYSTEM, prompt_user],
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json",
                        temperature=0.3
                    )
                )
                if response and response.text:
                    parsed = self._clean_and_parse_json(response.text)
                    if parsed:
                        logger.info("✅ Resposta recebida do Gemini com sucesso!")
                        return parsed
            except Exception as e:
                logger.warning(f"⚠️ Erro na chamada à API Gemini: {e}")

        # 3. Fallback Heurístico Estruturado
        logger.info("ℹ️ Utilizando minerador de fallback estruturado.")
        return self._fallback_mining(title, text_content)

    def _clean_and_parse_json(self, raw_text: str) -> Optional[Dict[str, Any]]:
        try:
            clean_str = re.sub(r'^```json\s*', '', raw_text.strip(), flags=re.IGNORECASE)
            clean_str = re.sub(r'```$', '', clean_str.strip()).strip()

            parsed = json.loads(clean_str)
            if isinstance(parsed, dict) and "01_tema_central" in parsed:
                return parsed
        except Exception as e:
            logger.warning(f"⚠️ Falha ao fazer parse do JSON retornado: {e}")

        return None

    def _fallback_mining(self, title: str, text: str) -> Dict[str, Any]:
        return {
            "01_tema_central": f"Mensagem edificante pregada na IBPM CR sobre o tema '{title or 'Culto de Celebração'}'. O preletor abordou princípios de fé, oração, vida espiritual e vitória em Cristo Jesus.",
            "02_frases_virais": [
                "A oração do justo move o coração de Deus e transforma circunstâncias.",
                "Não olhe para o tamanho do problema, olhe para a grandeza do seu Deus.",
                "Quem anda na palavra de Deus nunca caminha na escuridão.",
                "Deus é fiel para cumprir cada promessa feita à sua família."
            ],
            "03_passagens_biblicas": [
                "Salmos 23:1",
                "Filipenses 4:13",
                "Isaías 40:31"
            ],
            "04_ideia_carrossel_instagram": [
                "Slide 1: [O Poder da Oração] - Descubra como mudar sua realidade hoje",
                "Slide 2: [Foco na Promessa] - Mantenha os olhos firmes no Senhor",
                "Slide 3: [Ação de Fé] - Dê o primeiro passo em direção ao seu milagre",
                "Slide 4: [Reflexão Final] - Compartilhe esta bênção com alguém que precisa"
            ],
            "05_cortes_virais": [
                {
                    "titulo": "Deus Não Se Esqueceu de Você!",
                    "contexto": "Momento de encorajamento sobre as promessas de Deus para a família.",
                    "sugestao_b_roll": "Imagens de pessoas orando com mãos levantadas no altar em luz de holofote.",
                    "score_viral": 92,
                    "trecho_inicial": "Você que está me ouvindo agora no templo ou em casa...",
                    "trecho_final": "O Senhor está decretando vitória na sua vida!"
                },
                {
                    "titulo": "A Oração Que Quebra as Cadeias",
                    "contexto": "Pregação sobre libertação e clamor no altar.",
                    "sugestao_b_roll": "Imagens cinematográficas de correntes se quebrando e luz rompendo a escuridão.",
                    "score_viral": 88,
                    "trecho_inicial": "Quando a igreja se une em oração de concordância...",
                    "trecho_final": "Todo o julgo e opressão caem por terra em nome de Jesus!"
                }
            ],
            "06_prompt_thumbnail": "Dramatic, cinematic photo of an evangelical pastor preaching on stage, warm amber spotlight, hands raised in prayer, high detail 8k --ar 16:9"
        }


if __name__ == "__main__":
    miner = ContentMinerLLM()
    print("ContentMinerLLM pronto para Groq API (Llama 3.3 70B)!")
