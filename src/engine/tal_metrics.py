# -*- coding: utf-8 -*-
"""
Módulo TAL Metrics — Métricas de Localização de Ação Temporal (Temporal Action Localization)
e Emparelhamento via Algoritmo Húngaro (Kuhn-Munkres).
IBPM CR Automation System
"""

import numpy as np
from typing import List, Tuple, Dict, Any, NamedTuple
from scipy.optimize import linear_sum_assignment


class MétricasTAL(NamedTuple):
    precision: float
    recall: float
    f1_score: float
    boundary_rmse: float
    tp: int
    fp: int
    fn: int


def calcular_tIoU(previsto: Tuple[float, float], real: Tuple[float, float]) -> float:
    """
    Calcula o Temporal Intersection over Union (tIoU) entre dois intervalos temporais (início, fim).
    """
    p_inicio, p_fim = previsto
    g_inicio, g_fim = real

    intersecao = max(0.0, min(p_fim, g_fim) - max(p_inicio, g_inicio))
    uniao = max(p_fim, g_fim) - min(p_inicio, g_inicio)

    if uniao <= 0:
        return 0.0

    return float(intersecao / uniao)


def emparelhamento_algoritmo_hungaro(
    predicoes: List[Tuple[float, float]],
    gabaritos: List[Tuple[float, float]]
) -> List[Tuple[int, int, float]]:
    """
    Realiza o emparelhamento 1-para-1 ótimo entre segmentos previstos e gabaritos reais
    utilizando a Otimização Bipartida do Algoritmo Húngaro (Kuhn-Munkres).

    Retorna lista de triplas: (indice_predicao, indice_gabarito, tIoU_correspondente)
    """
    if not predicoes or not gabaritos:
        return []

    num_p = len(predicoes)
    num_g = len(gabaritos)

    # Matriz de custo para maximizar o tIoU total -> minimizar (-tIoU)
    cost_matrix = np.zeros((num_p, num_g), dtype=np.float64)

    for i, p in enumerate(predicoes):
        for j, g in enumerate(gabaritos):
            cost_matrix[i, j] = -calcular_tIoU(p, g)

    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    matches = []
    for r, c in zip(row_ind, col_ind):
        tiou_val = -cost_matrix[r, c]
        matches.append((r, c, float(tiou_val)))

    return matches


def calcular_metricas_tal(
    predicoes: List[Tuple[float, float]],
    gabaritos: List[Tuple[float, float]],
    threshold_tiou: float = 0.75
) -> MétricasTAL:
    """
    Calcula as métricas globais de TAL (Precision, Recall, F1@tIoU e Boundary RMSE)
    dado um limiar de exigência theta (ex: 0.75).
    """
    if not predicoes and not gabaritos:
        return MétricasTAL(precision=1.0, recall=1.0, f1_score=1.0, boundary_rmse=0.0, tp=0, fp=0, fn=0)

    if not predicoes:
        return MétricasTAL(precision=0.0, recall=0.0, f1_score=0.0, boundary_rmse=0.0, tp=0, fp=0, fn=len(gabaritos))

    if not gabaritos:
        return MétricasTAL(precision=0.0, recall=0.0, f1_score=0.0, boundary_rmse=0.0, tp=len(predicoes), fp=len(predicoes), fn=0)

    matches = emparelhamento_algoritmo_hungaro(predicoes, gabaritos)

    tp = 0
    boundary_sq_errors = []

    matched_p_indices = set()
    matched_g_indices = set()

    for idx_p, idx_g, tiou in matches:
        if tiou >= threshold_tiou:
            tp += 1
            matched_p_indices.add(idx_p)
            matched_g_indices.add(idx_g)

            p_in, p_fim = predicoes[idx_p]
            g_in, g_fim = gabaritos[idx_g]
            boundary_sq_errors.append((p_in - g_in) ** 2)
            boundary_sq_errors.append((p_fim - g_fim) ** 2)

    fp = len(predicoes) - tp
    fn = len(gabaritos) - tp

    precision = float(tp / (tp + fp)) if (tp + fp) > 0 else 0.0
    recall = float(tp / (tp + fn)) if (tp + fn) > 0 else 0.0

    if (precision + recall) > 0:
        f1 = float(2 * precision * recall / (precision + recall))
    else:
        f1 = 0.0

    if boundary_sq_errors:
        rmse = float(np.sqrt(np.mean(boundary_sq_errors)))
    else:
        rmse = 0.0

    return MétricasTAL(
        precision=precision,
        recall=recall,
        f1_score=f1,
        boundary_rmse=rmse,
        tp=tp,
        fp=fp,
        fn=fn
    )
