"""
Minerador NLP Clássico & Heurístico (Fase 3) - IBPM CR Automation System.

Executa a Mineração Teológica 100% LOCAL (0% LLM, 0% API, 0% Custo, Cota Ilimitada).
Analisa transcrições (.txt, .srt, .json) utilizando:
1. Algoritmo de Janela Deslizante (45 a 75 segundos).
2. Dicionário de Gatilhos Pentecostais & Homiléticos.
3. Densidade Semântica e Pontuação Enfática (! e ?).
4. Filtro de Blacklist de momentos administrativos (Dízimos, Avisos, Estacionamento).
5. Geração do arquivo relatorio_cortes.csv e do payload .insights.json compatível com a Fase 4.
"""

import sys
import os
import re
import json
import csv
from pathlib import Path
from typing import Dict, Any, List, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger

logger = get_logger("NLPHeuristicMiner")

# Dicionário de Gatilhos Pentecostais (Score Positivo)
PENTECOSTAL_TRIGGERS = [
    "preste atenção", "presta atenção", "o segredo é", "a bíblia diz", "a palavra diz",
    "não desista", "deus fala", "deus mandou te dizer", "olha para o seu irmão",
    "olha para o irmão", "tem milagre aqui", "receba essa palavra", "deus vai mudar",
    "veja bem", "escuta isso", "glória a deus", "aleluia", "amém", "espírito santo",
    "autoridade de deus", "fogo santo", "deus tem um plano", "resposta de deus",
    "deus está dizendo", "deus te trouxe aqui", "propósito", "vitória", "profetizo"
]

# Blacklist de Momentos Administrativos (Zeram o Score)
ADMINISTRATIVE_BLACKLIST = [
    "dízimo", "dízimos", "oferta", "ofertas", "avisos", "estacionamento",
    "secretaria", "boletim", "banco", "pix", "tesouraria", "comunicados",
    "banheiro", "saída", "cantina"
]


class NLPHeuristicMiner:
    """
    Minerador de Cortes por Algoritmo de NLP Clássico e Regras Heurísticas.
    """

    def __init__(self):
        logger.info("🧠 Inicializado Minerador NLP Clássico Heurístico (100% Local).")

    def format_timestamp(self, seconds: float) -> str:
        """Converte segundos para hh:mm:ss."""
        hrs = int(seconds // 3600)
        mins = int((seconds % 3600) // 60)
        secs = int(seconds % 60)
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"

    def calculate_window_score(self, text: str) -> float:
        """
        Calcula a pontuação (score) de uma janela de texto.
        """
        text_lower = text.lower()

        # 1. Filtro de Blacklist (Se contiver termos administrativos, zerar o score)
        for black_word in ADMINISTRATIVE_BLACKLIST:
            if re.search(r'\b' + re.escape(black_word) + r'\b', text_lower):
                return 0.0

        score = 10.0  # Pontuação base

        # 2. Gatilhos de Impacto Homilético (+15 pontos por gatilho)
        for trigger in PENTECOSTAL_TRIGGERS:
            matches = len(re.findall(re.escape(trigger), text_lower))
            score += matches * 15.0

        # 3. Densidade de Pontuação Enfática (+5 pontos por ! ou ?)
        empathic_count = len(re.findall(r'[!?]', text))
        score += empathic_count * 5.0

        # 4. Densidade de Palavras Relevantes
        word_count = len(text.split())
        if 80 <= word_count <= 220:
            score += 10.0  # Tamanho ideal para um Reel (45 a 65 segundos)

        return round(score, 2)

    def extract_7_words_anchor(self, words: List[str], start_idx: int) -> str:
        """Extrai exatamente 7 palavras consecutivas para âncora literal."""
        slice_words = words[start_idx:start_idx + 7]
        while len(slice_words) < 7:
            slice_words.append("palavra")
        return " ".join(slice_words)

    def analyze_transcript_heuristic(
        self,
        transcript_text: str,
        source_video_id: str = "IBPM_CULTO",
        job_id: str = "job_nlp_local"
    ) -> Dict[str, Any]:
        """
        Executa a mineração heurística baseada em Janela Deslizante de 50 segundos.
        Retorna o dicionário no formato exato da Fase 3 (.insights.json).
        """
        if not transcript_text or len(transcript_text.strip()) < 100:
            raise ValueError("Transcrição insuficiente para mineração NLP.")

        words = transcript_text.split()
        total_words = len(words)

        # Janela deslizante de ~120 palavras (~50 segundos de fala) com passo de 30 palavras
        window_size = 120
        step_size = 30

        scored_windows = []

        for i in range(0, max(1, total_words - window_size), step_size):
            window_words = words[i:i + window_size]
            window_str = " ".join(window_words)
            score = self.calculate_window_score(window_str)

            # Estimar timestamps aproximados (130 palavras por minuto = 2.16 palavras por segundo)
            approx_start_sec = round(i / 2.16, 1)
            approx_end_sec = round((i + len(window_words)) / 2.16, 1)

            if score > 0:
                scored_windows.append({
                    "start_idx": i,
                    "words": window_words,
                    "text": window_str,
                    "score": score,
                    "start_sec": approx_start_sec,
                    "end_sec": approx_end_sec,
                    "start_anchor": self.extract_7_words_anchor(words, i),
                    "end_anchor": self.extract_7_words_anchor(words, min(total_words - 7, i + len(window_words) - 7))
                })

        # Ordenar por score decrescente
        scored_windows.sort(key=lambda x: x["score"], reverse=True)

        # Selecionar Top 3 Short-Form (9:16) sem sobreposição
        selected_shorts = []
        for w in scored_windows:
            if len(selected_shorts) >= 3:
                break
            # Evitar sobreposição com cortes já selecionados
            overlap = any(abs(w["start_sec"] - prev["start_sec"]) < 60 for prev in selected_shorts)
            if not overlap:
                selected_shorts.append(w)

        # Selecionar Top 2 Mid-Form (16:9)
        selected_mids = []
        for idx in range(0, min(len(words), total_words - 600), 600):
            mid_slice = words[idx:idx + 600]
            mid_text = " ".join(mid_slice)
            mid_score = self.calculate_window_score(mid_text)
            if mid_score > 0 and len(selected_mids) < 2:
                mid_start_sec = round(idx / 2.16, 1)
                mid_end_sec = round((idx + 600) / 2.16, 1)
                selected_mids.append({
                    "cut_id": f"mid_{len(selected_mids)+1:03d}",
                    "title_hook_a": f"Mensagem Exegética - Parte {len(selected_mids)+1}",
                    "title_hook_b": "Exposição Bíblica Profunda",
                    "start_anchor_7_words": self.extract_7_words_anchor(words, idx),
                    "end_anchor_7_words": self.extract_7_words_anchor(words, min(total_words - 7, idx + 593)),
                    "category": "Exegese",
                    "emotional_tone": "Reflexivo",
                    "start_sec": mid_start_sec,
                    "end_sec": mid_end_sec,
                    "score": mid_score
                })

        # Montar lista no padrão Short-Form da Fase 3
        short_cuts_payload = []
        for idx, s in enumerate(selected_shorts, 1):
            short_cuts_payload.append({
                "cut_id": f"short_{idx:03d}",
                "title_hook_a": f"Impacto Teológico #{idx}",
                "title_hook_b": f"Revelação de Fé - Parte #{idx}",
                "start_anchor_7_words": s["start_anchor"],
                "end_anchor_7_words": s["end_anchor"],
                "category": "Gatilho Profético",
                "emotional_tone": "Inspirador",
                "start_sec": s["start_sec"],
                "end_sec": s["end_sec"],
                "score": s["score"],
                "text_snippet": s["text"][:150] + "..."
            })

        insights_payload = {
            "job_id": job_id,
            "source_video_id": source_video_id,
            "sermon_title": f"Culto IBPM CR {source_video_id}",
            "preacher_name": "Pastor IBPM CR",
            "short_form_cuts": short_cuts_payload,
            "mid_form_cuts": selected_mids
        }

        # Salva o relatorio_cortes.csv
        self.export_relatorio_csv(source_video_id, short_cuts_payload + selected_mids)

        return insights_payload

    def export_relatorio_csv(self, source_file: str, cuts: List[Dict[str, Any]]) -> str:
        """Exporta os cortes minerados para data/relatorio_cortes.csv."""
        csv_path = Path("data/relatorio_cortes.csv")
        csv_path.parent.mkdir(parents=True, exist_ok=True)

        file_exists = csv_path.exists()

        with open(csv_path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow([
                    "arquivo_origem", "corte_id", "timestamp_inicio",
                    "timestamp_fim", "duracao_segundos", "score", "texto_do_corte"
                ])

            for c in cuts:
                s_sec = c.get("start_sec", 0.0)
                e_sec = c.get("end_sec", 45.0)
                dur = round(e_sec - s_sec, 1)
                writer.writerow([
                    source_file,
                    c.get("cut_id"),
                    self.format_timestamp(s_sec),
                    self.format_timestamp(e_sec),
                    dur,
                    c.get("score", 50.0),
                    c.get("title_hook_a", "Corte Minerado")
                ])

        logger.info(f"📊 Relatório atualizado em {csv_path}")
        return str(csv_path)
