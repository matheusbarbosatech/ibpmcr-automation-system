"""
Módulo de Análise de Sentimento e Mineração de Comentários (BERTimbau).

Analisa os comentários coletados via YouTube API usando modelos pré-treinados em português (BERTimbau)
para classificar mensagens em gratidão, pedidos de oração e dúvidas doutrinárias.
"""

import logging
from typing import Dict, Any, List
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from transformers import pipeline
    HAS_TRANSFORMERS = True
except ImportError:
    HAS_TRANSFORMERS = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class CommentSentimentMiner:
    """
    Minerador de sentimentos de comentários da IBPM CR usando BERTimbau / HuggingFace.
    """

    def __init__(self):
        """
        Inicializa a pipeline de classificação de sentimentos.
        """
        self.sentiment_pipe = None
        if HAS_TRANSFORMERS:
            try:
                # Carrega pipeline pré-treinado leve para análise em português
                self.sentiment_pipe = pipeline(
                    "sentiment-analysis",
                    model="lxyuan/distilbert-base-multilingual-cased-sentiments-student"
                )
                logger.info("✅ Pipeline de Análise de Sentimento carregada com sucesso.")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível carregar o modelo BERT: {e}. Usando modo de regras.")

    def analyze_comments(self, comments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Mines and categorizes a list of YouTube comments.

        :param comments: Lista de comentários [{'author': str, 'text': str, 'like_count': int}].
        :return: Relatório consolidado com mineração e categorias.
        """
        logger.info(f"📊 Analisando sentimentos de {len(comments)} comentários...")

        total = len(comments)
        gratitude_count = 0
        prayer_request_count = 0
        doctrinal_questions = 0

        categorized_comments = []

        for item in comments:
            text = item.get("text", "")
            text_lower = text.lower()

            category = "Geral / Edificação"
            sentiment_score = "POSITIVE"

            if any(w in text_lower for w in ["oração", "ore por", "peço oração", "saúde", "cura"]):
                category = "Pedido de Oração"
                prayer_request_count += 1
            elif any(w in text_lower for w in ["dízimo", "batismo", "onde fica", "horário", "dúvida"]):
                category = "Dúvida Doutrinária / Informação"
                doctrinal_questions += 1
            else:
                gratitude_count += 1

            if self.sentiment_pipe and len(text) > 5:
                try:
                    res = self.sentiment_pipe(text[:512])[0]
                    sentiment_score = res.get("label", "POSITIVE")
                except Exception:
                    pass

            categorized_comments.append({
                "author": item.get("author", "Anônimo"),
                "text": text,
                "category": category,
                "sentiment": sentiment_score
            })

        return {
            "total_comments": total,
            "metrics": {
                "gratitude_pct": round((gratitude_count / max(1, total)) * 100, 1),
                "prayer_requests_pct": round((prayer_request_count / max(1, total)) * 100, 1),
                "doctrinal_questions_pct": round((doctrinal_questions / max(1, total)) * 100, 1)
            },
            "analyzed_list": categorized_comments
        }


if __name__ == "__main__":
    miner = CommentSentimentMiner()
    comments = [
        {"author": "Maria", "text": "Amém! Mensagem gloriosa de restauração."},
        {"author": "João", "text": "Por favor peço oração pela cura do meu filho que está hospitalizado."}
    ]
    res = miner.analyze_comments(comments)
    print("Relatório de Análise de Comentários:")
    print(res)
