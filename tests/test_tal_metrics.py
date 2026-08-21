# -*- coding: utf-8 -*-
"""
Testes Unitários TAL Metrics & Regressão em Lote (Ground-Truth, tIoU e Algoritmo Húngaro)
IBPM CR Automation System
"""

import pytest
from src.engine.tal_metrics import (
    calcular_tIoU,
    emparelhamento_algoritmo_hungaro,
    calcular_metricas_tal
)
from src.engine.batch_regression import RegressãoBatchRunner


def test_calcular_tiou_fronteiras_perfeitas_e_disjuntas():
    # 1. Sobreposição Perfeita (tIoU = 1.0)
    assert calcular_tIoU((10.0, 30.0), (10.0, 30.0)) == pytest.approx(1.0)

    # 2. Segmentos Disjuntos (tIoU = 0.0)
    assert calcular_tIoU((10.0, 20.0), (30.0, 40.0)) == pytest.approx(0.0)

    # 3. Sobreposição Parcial (Interseção 10.0 a 20.0 = 10; União 0.0 a 30.0 = 30; tIoU = 1/3)
    assert calcular_tIoU((0.0, 20.0), (10.0, 30.0)) == pytest.approx(10.0 / 30.0)


def test_emparelhamento_algoritmo_hungaro_otimizacao():
    predicoes = [(10.0, 30.0), (100.0, 150.0)]
    gabaritos = [(12.0, 32.0), (200.0, 250.0)]

    matches = emparelhamento_algoritmo_hungaro(predicoes, gabaritos)
    assert len(matches) == 2

    # O primeiro par deve ter tIoU alto e o segundo par tIoU baixo/nulo
    matched_pairs = {m[0]: (m[1], m[2]) for m in matches}
    assert matched_pairs[0][0] == 0
    assert matched_pairs[0][1] > 0.7


def test_calcular_metricas_tal_precision_recall_f1():
    predicoes = [(10.0, 30.0), (50.0, 70.0), (100.0, 120.0)]
    gabaritos = [(10.0, 30.0), (50.0, 70.0)]

    metricas = calcular_metricas_tal(predicoes, gabaritos, threshold_tiou=0.75)
    assert metricas.tp == 2
    assert metricas.fp == 1
    assert metricas.fn == 0
    assert metricas.precision == pytest.approx(2.0 / 3.0)
    assert metricas.recall == pytest.approx(1.0)
    assert metricas.f1_score == pytest.approx(4.0 / 5.0)


def test_regressao_batch_runner_margem_tolerancia():
    runner = RegressãoBatchRunner(tolerancia_regressao_pct=1.5)

    predicoes = {"v1": [(10.0, 30.0), (50.0, 70.0)]}
    gabaritos = {"v1": [(10.0, 30.0), (50.0, 70.0)]}

    res = runner.avaliar_lote(predicoes, gabaritos, baseline_f1=0.75, threshold_tiou=0.75)
    assert res["aprovado"] is True
    assert res["f1_atual"] == 1.0
