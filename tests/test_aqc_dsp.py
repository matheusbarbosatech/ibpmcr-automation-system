# -*- coding: utf-8 -*-
"""
Testes Unitários AQC DSP — Sinais Artificiais NumPy e Cadência WPM
IBPM CR Automation System
"""

import pytest
import numpy as np
from src.engine.aqc_dsp import AnalisadorDSP, MotorCadencia


def test_clipping_ratio_em_ondas_senoidais_saturadas():
    # Organizar: Construir ondas senoidais e gerar ceifamento intencional do espectro
    taxa_amostragem = 22050
    t = np.linspace(0, 1.0, taxa_amostragem) # 1 segundo linear discreto
    sinal_puro = np.sin(2 * np.pi * 440 * t) # Lá harmônico limpo (440Hz)

    # Aplicar corte saturador superior e inferior ao nível 0.9 do espectro contínuo [-1,1]
    sinal_distorcido = np.clip(sinal_puro, -0.9, 0.9)

    analisador = AnalisadorDSP()

    # Agir: Computar as amostras sobre o tensor
    resultado_clipping = analisador.calcular_clipping_ratio(sinal_distorcido, threshold=0.9)

    # Afirmar: A medição de amostras limadas (achatamento) reflete anomalia alta (>0.05).
    assert resultado_clipping > 0.05
    assert analisador.avalia_distorcao_fatal(resultado_clipping) is True


def test_pontuacao_de_cadencia_anormal_rejeita_corte():
    # Organizar: 350 palavras (alto WPM em pouco tempo) simula descompasso das legendas e áudio
    motor = MotorCadencia()
    quantidade_extrema = 350
    texto_rapido = "Avante " * quantidade_extrema
    janela_segundos = 60.0

    # Agir
    score_gerado = motor.computar_pontuacao_wpm(texto_rapido, janela_segundos)

    # Afirmar: Métrica sobrepassa tolerâncias de fluência humana normal, ativando dedução de scores limitantes
    assert score_gerado.wpm == 350
    assert score_gerado.pontos < 70 # Dedutibilidade penalizadora leva para zona REJEITADO
    assert score_gerado.veredito == "REJEITADO"
