"""
Módulo Detector de Testemunhos via NER (spaCy).

Varre transcrições dos cultos da IBPM CR identificando relatos de curas, milagres,
restauração familiar e vitórias espirituais, marcando-os para o 'Mural de Testemunhos'.
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


class TestimonyDetectorNER:
    """
    Detector de estruturas narrativas de testemunho e milagres.
    """

    TESTIMONY_TRIGGERS = [
        "testemunho", "milagre", "curou", "cura", "libertação", "vitoria", "vitória",
        "deus fez", "graça alcancei", "médico disse", "porta se abriu", "restaurou"
    ]

    def __init__(self, model_name: str = SPACY_MODEL):
        """
        Inicializa a pipeline spaCy.
        """
        self.nlp = None
        if HAS_SPACY:
            try:
                self.nlp = spacy.load(model_name)
            except Exception as e:
                logger.warning(f"spaCy não carregado: {e}")

    def extract_testimonies(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Analisa os segmentos da transcrição e isola trechos contendo relatos de testemunho.

        :param segments: Lista de segmentos da transcrição [{'start': float, 'end': float, 'text': str}].
        :return: Lista de testemunhos identificados para o Mural de Testemunhos.
        """
        logger.info(f"✨ Varendo {len(segments)} segmentos da transcrição em busca de testemunhos...")

        detected = []
        for seg in segments:
            text_lower = seg["text"].lower()
            if any(trigger in text_lower for trigger in self.TESTIMONY_TRIGGERS):
                entities = self._extract_entities(seg["text"])
                detected.append({
                    "start": seg["start"],
                    "end": seg["end"],
                    "text": seg["text"],
                    "entities": entities,
                    "category": self._categorize_testimony(text_lower)
                })

        logger.info(f"✅ {len(detected)} relatos de testemunho identificados!")
        return detected

    def _extract_entities(self, text: str) -> List[Dict[str, str]]:
        """Extrai pessoas, locais e datas usando spaCy NER."""
        if not self.nlp:
            return []

        doc = self.nlp(text)
        return [{"text": ent.text, "label": ent.label_} for ent in doc.ents]

    def _categorize_testimony(self, text: str) -> str:
        if any(w in text for w in ["cura", "médico", "saúde", "enfermidade"]):
            return "Cura e Saúde"
        elif any(w in text for w in ["porta", "trabalho", "emprego", "financeiro"]):
            return "Provisão e Emprego"
        elif any(w in text for w in ["família", "casamento", "filho"]):
            return "Restauração Familiar"
        return "Milagre e Libertação"


if __name__ == "__main__":
    detector = TestimonyDetectorNER()
    sample_segs = [
        {"start": 10.0, "end": 40.0, "text": "Quero contar o testemunho da irmã Maria. O médico disse que não havia cura, mas Deus fez o milagre!"},
        {"start": 45.0, "end": 70.0, "text": "Vamos cantar o hino de encerramento do culto."}
    ]
    res = detector.extract_testimonies(sample_segs)
    print("Testemunhos encontrados:")
    print(res)
