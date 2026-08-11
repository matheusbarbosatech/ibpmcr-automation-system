"""
Módulo de Mineração de Texto e Classificação Temática (content_analyzer.py).

Analisa o texto transcrito usando Processamento de Linguagem Natural (spaCy) e MAPEIA
as minutagens exatas (sem renderizar nem cortar nenhum vídeo nesta etapa) para:
1. Cortes Curtos 9:16 (30s - 60s)
2. Cortes Médios 16:9 (5min - 15min) por tema (Oração, Família, Fé, Libertação)
3. Potencial para E-books e Devocionais em PDF
4. Potencial para EBD Kids (histórias infantis)
5. Bloco de Louvores Executados
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


class ContentAnalyzer:
    """
    Minerador semântico de transcrições para geração do Plano Mestre de Mídia.
    """

    THEME_KEYWORDS = {
        "Oracao": ["oração", "orar", "clamor", "intercessão", "joelho", "madrugada"],
        "Familia": ["família", "casamento", "esposa", "marido", "filhos", "lar", "pais"],
        "Fe": ["fé", "milagre", "confiança", "promessa", "vitória", "impossível", "graça"],
        "Libertacao": ["libertação", "quebra de correntes", "cura", "restauração", "transformação", "autoridade"]
    }

    SHORT_TRIGGERS = [
        "fogo", "glória", "poder", "olha para o irmão", "receba", "deus manda te dizer",
        "vitória", "milagre", "forte", "impacto", "atenção"
    ]

    KIDS_TRIGGERS = [
        "crianças", "criancinhas", "pequeninos", "historinha", "davi e golias",
        "arca de noé", "jesus ama as crianças", "obediência"
    ]

    def __init__(self, model_name: str = SPACY_MODEL):
        """
        Inicializa a pipeline spaCy em português.
        """
        self.nlp = None
        if HAS_SPACY:
            try:
                self.nlp = spacy.load(model_name)
                logger.info(f"✅ spaCy ({model_name}) carregado para mineração de texto.")
            except Exception as e:
                logger.warning(f"spaCy indisponível ({e}). Usando modo heurístico.")

    def analyze_transcript(self, transcript_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analisa os segmentos de tempo da transcrição e constrói o plano de cortes sem renderizar mídia.

        :param transcript_data: Dados vindos do transcriber_batch.py.
        :return: Dicionário contendo o mapa de potencial de mídia.
        """
        segments = transcript_data.get("segmentos_timestamps", [])
        full_text = transcript_data.get("texto_completo", "")

        logger.info(f"🧠 Minando texto transcrito ({len(segments)} segmentos) para o Plano Mestre...")

        # 1. Mapeamento de Louvores (Geralmente nos primeiros 10-15 minutos)
        worship_block = self._map_worship_block(segments)

        # 2. Mapeamento de Cortes Curtos 9:16 (30-60 segundos)
        short_clips = self._map_short_clips(segments)

        # 3. Mapeamento de Cortes Médios 16:9 (5-15 minutos) por Tema
        medium_clips = self._map_medium_clips(segments)

        # 4. Avaliação de Potencial para E-books e Devocionais
        ebook_potential = self._assess_ebook_potential(full_text)

        # 5. Avaliação de Potencial para EBD Kids
        kids_potential = self._assess_kids_potential(segments)

        return {
            "louvores_executados_bloco": worship_block,
            "potencial_cortes_curtos_9_16": short_clips,
            "potencial_cortes_medios_16_9": medium_clips,
            "potencial_ebook_devocional": ebook_potential,
            "potencial_ebd_kids": kids_potential
        }

    def _map_worship_block(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Mapeia o bloco inicial de louvor congregacional."""
        worship_segs = [s for s in segments if s["start_sec"] <= 900 and any(w in s["text"].lower() for w in ["louvor", "hino", "cantar", "senhor", "adorar"])]
        if worship_segs:
            return {
                "start_sec": worship_segs[0]["start_sec"],
                "end_sec": worship_segs[-1]["end_sec"],
                "descricao": "Bloco inicial de louvor e adoração congregacional"
            }
        return {"start_sec": 0.0, "end_sec": 600.0, "descricao": "Bloco padrão de abertura e louvor"}

    def _map_short_clips(self, segments: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Mapeia trechos espirituais curtos (30 a 60 segundos) com alto potencial de engajamento."""
        shorts = []
        for seg in segments:
            text_lower = seg["text"].lower()
            duration = seg["end_sec"] - seg["start_sec"]

            # Procura por gatilhos de impacto espiritual ou ajusta trechos de 30-60s
            if any(trig in text_lower for trig in self.SHORT_TRIGGERS) or (30.0 <= duration <= 60.0):
                shorts.append({
                    "start_sec": seg["start_sec"],
                    "end_sec": min(seg["start_sec"] + 55.0, seg["end_sec"]),
                    "duracao_segundos": round(min(55.0, duration), 1),
                    "gatilho_identificado": "Reflexão Espiritual / Fogo",
                    "texto_resumo": seg["text"][:120] + "..."
                })

        return shorts[:5]  # Retorna os top 5 melhores recortes curtos mapeados

    def _map_medium_clips(self, segments: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Mapeia blocos contínuos de 5 a 15 minutos categorizados por temas."""
        categorized = {"Oracao": [], "Familia": [], "Fe": [], "Libertacao": []}

        for seg in segments:
            text_lower = seg["text"].lower()
            for theme, keywords in self.THEME_KEYWORDS.items():
                if any(kw in text_lower for kw in keywords):
                    # Projeta um bloco contínuo de 5 a 10 minutos em volta do segmento
                    start_sec = max(0.0, seg["start_sec"] - 30.0)
                    end_sec = start_sec + 450.0  # 7.5 minutos
                    categorized[theme].append({
                        "tema": theme,
                        "start_sec": round(start_sec, 1),
                        "end_sec": round(end_sec, 1),
                        "duracao_minutos": round((end_sec - start_sec) / 60.0, 1),
                        "resumo_tema": seg["text"][:150]
                    })
                    break

        return categorized

    def _assess_ebook_potential(self, full_text: str) -> Dict[str, Any]:
        """Avalia se a pregação tem estrutura bíblica expositiva para virar e-book PDF."""
        text_lower = full_text.lower()
        score = 0
        if any(w in text_lower for w in ["livro de", "capítulo", "versículo"]):
            score += 40
        if any(w in text_lower for w in ["primeiro", "segundo", "conclusão", "em resumo"]):
            score += 30
        if len(full_text) > 3000:
            score += 30

        has_potential = score >= 60
        return {
            "apropriado_para_ebook": has_potential,
            "score_estrutural": score,
            "recomendacao": "Sermão expositivo com estrutura bíblica clara para e-book" if has_potential else "Mensagem espontânea"
        }

    def _assess_kids_potential(self, segments: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Avalia se a mensagem contém ilustrações ou histórias bíblicas adaptáveis para EBD Kids."""
        kids_segs = []
        for s in segments:
            if any(trig in s["text"].lower() for trig in self.KIDS_TRIGGERS):
                kids_segs.append(s)

        return {
            "apropriado_para_ebd_kids": len(kids_segs) > 0,
            "trechos_identificados": len(kids_segs),
            "recomendacao": "Contém narrativas bíblicas adaptáveis para lições infantis" if kids_segs else "Linguagem voltada predominantemente ao público adulto"
        }


if __name__ == "__main__":
    analyzer = ContentAnalyzer()
    dummy_data = {
        "texto_completo": "Capítulo doze de Romanos ensina sobre a renovação da mente e o culto racional. Quando oramos com fé, a família é abençoada.",
        "segmentos_timestamps": [
            {"segment_id": 1, "start_sec": 10.0, "end_sec": 45.0, "text": "Receba a resposta de Deus no seu coração neste momento de oração!"},
            {"segment_id": 2, "start_sec": 50.0, "end_sec": 400.0, "text": "Estudo sobre a restauração do casamento e da família no livro de Efésios."}
        ]
    }
    res = analyzer.analyze_transcript(dummy_data)
    print("Mapa do Plano Mestre de Mídia gerado:")
    print("Cortes curtos mapeados:", len(res["potencial_cortes_curtos_9_16"]))
