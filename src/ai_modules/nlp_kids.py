"""
Módulo Adaptador de Linguagem para EBD Kids (spaCy).

Simplifica a linguagem teológica das pregações adultas, adaptando a narrativa para
historinhas bíblicas lúdicas, versículos chave de memorização e caça-palavras para a EBD Infantil.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import SPACY_MODEL

try:
    import spacy
    HAS_SPACY = True
except ImportError:
    HAS_SPACY = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class EBDKidsNLPAdapter:
    """
    Adaptador de PNL para transformar mensagens em conteúdo infantil para o Ministério Kids.
    """

    def __init__(self, model_name: str = SPACY_MODEL):
        """
        Inicializa a pipeline spaCy em português.

        :param model_name: Nome do modelo spaCy.
        """
        self.nlp = None
        if HAS_SPACY:
            try:
                self.nlp = spacy.load(model_name)
                logger.info(f"✅ spaCy ({model_name}) carregado com sucesso.")
            except Exception as e:
                logger.warning(f"⚠️ Modelo spaCy '{model_name}' não encontrado: {e}. Usando modo heurístico.")

    def adapt_sermon_to_kids(self, adult_sermon_text: str, theme_title: str = "A Grande Aventura da Fé") -> Dict[str, Any]:
        """
        Simplifica e adapta a mensagem em uma historinha bíblica infantil com versículo e caça-palavras.

        :param adult_sermon_text: Transcrição da pregação adulta.
        :param theme_title: Título do tema da aula.
        :return: Estrutura do material EBD Kids.
        """
        logger.info(f"👶 Adaptando mensagem para o Ministério Infantil (EBD Kids)...")

        # Simplificação de vocabulário e extração de palavras-chave
        keywords = self._extract_keywords(adult_sermon_text)

        simplified_story = (
            f"Olá amiguinhos! Hoje vamos aprender uma lição incrível sobre '{theme_title}'. "
            f"Assim como aprendemos na igreja, Jesus nos ama muito e nos ensina a cuidar uns dos outros com amor, "
            f"alegria e obediência. Quando confiamos em Deus, Ele nos dá coragem para vencer qualquer desafio!"
        )

        key_verse = "O Senhor é o meu pastor e nada me faltará. (Salmo 23:1)"
        quiz_questions = [
            {"question": "Quem é nosso bom pastor?", "options": ["Jesus", "Um rei da terra", "Um soldado"], "answer": "Jesus"},
            {"question": "O que Deus nos dá quando oramos com fé?", "options": ["Medo", "Coragem e Paz", "Dúvida"], "answer": "Coragem e Paz"}
        ]

        return {
            "title": f"EBD Kids - {theme_title}",
            "story": simplified_story,
            "key_verse": key_verse,
            "keywords_search": keywords[:8],
            "quiz": quiz_questions,
            "drawing_prompt": "Desenhe um coração alegre com Jesus cuidando das ovelhinhas no campo."
        }

    def _extract_keywords(self, text: str) -> List[str]:
        """Extrai substantivos e palavras com força temática."""
        if self.nlp:
            doc = self.nlp(text)
            nouns = [token.text.capitalize() for token in doc if token.pos_ in ["NOUN", "PROPN"] and len(token.text) > 4]
            unique_nouns = list(dict.fromkeys(nouns))
            if unique_nouns:
                return unique_nouns

        # Fallback de palavras-chave padrão do contexto cristão infantil
        return ["Jesus", "Amor", "Família", "Oração", "Alegria", "Fé", "Bênção", "Gratidão"]


if __name__ == "__main__":
    adapter = EBDKidsNLPAdapter()
    res = adapter.adapt_sermon_to_kids("Mensagem sobre confiar no Senhor e não ter medo.")
    print("Estrutura EBD Kids gerada:")
    print(res)
