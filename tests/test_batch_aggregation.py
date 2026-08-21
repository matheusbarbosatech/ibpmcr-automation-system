# -*- coding: utf-8 -*-
"""
Testes Unitários Dashboard Analytics — Agregação em Lote e Truncamento de Anomalias Físicas
IBPM CR Automation System
"""

import pytest
from src.dashboard_analytics import ColetorEstatistico, RegistroVeredito


def test_agregador_batch_trunca_anomalias_mantendo_massa():
    # Organizar: Conjunto em simulação de saídas do pipeline multifio com instabilidades
    agregador = ColetorEstatistico(capacidade_alvo=5)
    amostras_processadas = [
        RegistroVeredito(id_corte="c01", situacao="APROVADO", score=90.0),
        RegistroVeredito(id_corte="c02", situacao="REJEITADO", score=65.0), # Queda cadência WPM
        RegistroVeredito(id_corte="c03", situacao="APROVADO", score=80.0),
        RegistroVeredito(id_corte="c04", erro_critico=True), # Permissão corrompida / Arquivo sumiu
        RegistroVeredito(id_corte="c05", situacao="APROVADO", score=88.0),
    ]

    # Agir: Coleta e unificação das métricas do agrupamento global
    for amostra in amostras_processadas:
        agregador.acumular(amostra)
    relatorio = agregador.digerir_sumario_estatistico()

    # Afirmar: A consolidação ignora elementos crônicos falhos nas médias vitais de triagem.
    assert relatorio["tamanho_total"] == 5
    assert relatorio["media_pontuacao_qualificados"] == pytest.approx(86.0) # Média de 90, 80 e 88
    # Taxa de aprovação avaliada sobre volume efetivamente processável (sucesso lógico e físico = 4 arquivos)
    assert relatorio["taxa_aprovados"] == 75.0 # 3 aprovados sobre 4 efetivos
    assert relatorio["incidentes_irrecuperaveis"] == 1
