# -*- coding: utf-8 -*-
"""
Módulo Batch Regression — Suíte de Testes de Regressão em Lote e Gold Standard Dataset
IBPM CR Automation System
"""

from typing import List, Dict, Tuple, Any
from .tal_metrics import calcular_metricas_tal, MétricasTAL


class RegressãoBatchRunner:
    """
    Executa avaliação de acurácia global do pipeline contra o Gold Standard Dataset.
    Garante ausência de regressões silenciosas no modelo de mineração.
    """

    def __init__(self, tolerancia_regressao_pct: float = 1.5):
        self.tolerancia_regressao = tolerancia_regressao_pct / 100.0

    def avaliar_lote(
        self,
        predicoes_por_video: Dict[str, List[Tuple[float, float]]],
        gabaritos_por_video: Dict[str, List[Tuple[float, float]]],
        baseline_f1: float = 0.75,
        threshold_tiou: float = 0.75
    ) -> Dict[str, Any]:
        """
        Calcula as métricas agregadas do lote e valida se a diferença em relação à baseline
        está dentro da margem de tolerância.
        """
        todas_predicoes = []
        todos_gabaritos = []

        for video_id, gabarito in gabaritos_por_video.items():
            pred = predicoes_por_video.get(video_id, [])
            todas_predicoes.extend(pred)
            todos_gabaritos.extend(gabarito)

        metricas = calcular_metricas_tal(todas_predicoes, todos_gabaritos, threshold_tiou=threshold_tiou)

        f1_atual = metricas.f1_score
        f1_minimo = baseline_f1 - self.tolerancia_regressao
        aprovado = f1_atual >= f1_minimo

        return {
            "f1_atual": round(f1_atual, 4),
            "baseline_f1": round(baseline_f1, 4),
            "f1_minimo_aceitavel": round(f1_minimo, 4),
            "precision": round(metricas.precision, 4),
            "recall": round(metricas.recall, 4),
            "boundary_rmse": round(metricas.boundary_rmse, 4),
            "aprovado": aprovado,
            "detalhes": metricas
        }
