"""
Motor de Sincronia Temporal e Alinhamento Fuzzy - IBPM CR Automation System.

Utiliza busca por Janela Deslizante (Sliding Window), Distância de Levenshtein Normalizada
(via rapidfuzz) e o Protocolo de Degradação Graciosa em 4 passos para alinhar as âncoras
literais de 7 palavras do Gemini aos timestamps exatos em milissegundos do Faster-Whisper.
"""

import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import distance

from src.core.logger import get_logger

logger = get_logger("AnchorAligner")

FILLER_WORDS_REGEX = re.compile(
    r'\b(né|amém|irmãos|glória|tá|sabe|tipo|assim|néh|ômed)\b',
    flags=re.IGNORECASE
)


def sanitize_text_for_alignment(text: str) -> str:
    """
    Remove vícios de linguagem da oratória e pontuação para otimizar o casamento de strings.
    """
    text_clean = FILLER_WORDS_REGEX.sub('', text)
    text_clean = re.sub(r'[^\w\s]', '', text_clean)
    return re.sub(r'\s+', ' ', text_clean).strip().lower()


class AnchorAligner:
    """
    Alinhador de Âncoras Nominais de 7 Palavras com resiliência a erros de transcrição fonética.
    """

    def __init__(self, distance_threshold: float = 0.30):
        self.distance_threshold = distance_threshold

    def align_anchor_to_timestamps(
        self,
        whisper_words: List[Dict[str, Any]],
        anchor_text: str,
        is_end_anchor: bool = False,
        job_id: str = "job_alignment"
    ) -> Tuple[float, str]:
        """
        Calcula o timestamp exato em segundos (start_sec ou end_sec) para uma âncora de 7 palavras.
        Retorna (timestamp_sec, nivel_confianca).
        """
        if not whisper_words or not anchor_text:
            logger.warning("Palavras do Whisper ou âncora ausentes", job_id=job_id)
            return (0.0, "low_confidence_fallback")

        clean_anchor = sanitize_text_for_alignment(anchor_text)
        anchor_words = clean_anchor.split()
        window_size = max(3, len(anchor_words))

        best_distance = 1.0
        best_timestamp = 0.0
        best_matched_text = ""

        # Passo 1: Busca por Janela Deslizante (Sliding Window)
        for i in range(len(whisper_words) - window_size + 1):
            window_slice = whisper_words[i: i + window_size]
            window_text = " ".join([w.get("word", "").strip() for w in window_slice])
            clean_window = sanitize_text_for_alignment(window_text)

            # Distância de Levenshtein Normalizada Dn(A, B)
            d_norm = distance.NormalizedLevenshtein.distance(clean_anchor, clean_window)

            if d_norm < best_distance:
                best_distance = d_norm
                best_matched_text = clean_window
                
                # Seleciona o timestamp inicial ou final do bloco
                if is_end_anchor:
                    best_timestamp = float(window_slice[-1].get("end_sec", window_slice[-1].get("end", 0.0)))
                else:
                    best_timestamp = float(window_slice[0].get("start_sec", window_slice[0].get("start", 0.0)))

                if best_distance <= 0.05:  # Casamento perfeito
                    break

        logger.info(
            "Alinhamento por Janela Deslizante executado",
            job_id=job_id,
            best_distance=round(best_distance, 3),
            matched_timestamp=best_timestamp,
            is_end=is_end_anchor
        )

        # Se o alinhamento primário for aprovado (Dn <= 0.30)
        if best_distance <= self.distance_threshold:
            return (best_timestamp, "high_confidence_exact")

        # Passo 2: Protocolo de Degradação Graciosa (Fallback via N-Grams de 5 e 3 palavras)
        logger.warning(
            "Limiar de Levenshtein (0.30) ultrapassado. Ativando Degradação Graciosa.",
            job_id=job_id,
            best_distance=round(best_distance, 3)
        )

        for ngram_size in [5, 3]:
            if len(anchor_words) >= ngram_size:
                sub_anchor = " ".join(anchor_words[:ngram_size])
                for i in range(len(whisper_words) - ngram_size + 1):
                    window_slice = whisper_words[i: i + ngram_size]
                    clean_window = sanitize_text_for_alignment(" ".join([w.get("word", "").strip() for w in window_slice]))
                    d_norm = distance.NormalizedLevenshtein.distance(sub_anchor, clean_window)

                    if d_norm <= 0.25:
                        timestamp = float(window_slice[-1].get("end_sec", window_slice[-1].get("end", 0.0))) if is_end_anchor else float(window_slice[0].get("start_sec", window_slice[0].get("start", 0.0)))
                        logger.info("Alinhamento aceito via N-Grams Fallback", job_id=job_id, ngram=ngram_size, timestamp=timestamp)
                        return (timestamp, f"medium_confidence_ngram_{ngram_size}")

        # Passo 4: Aceite com Flag de Baixa Confiança
        return (best_timestamp, "low_confidence_fallback")
