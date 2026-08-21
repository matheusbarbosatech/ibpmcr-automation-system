# -*- coding: utf-8 -*-
"""
Testes Unitários AudioSlicerIO — Interceptação Subprocess FFmpeg e Aritmética de Margem Respiratória
IBPM CR Automation System
"""

import subprocess
import pytest
from unittest.mock import patch, MagicMock
from src.engine.io_manager import AudioSlicerIO, ErroProcessoVideo


@patch("subprocess.run")
def test_matematica_de_respiro_ffmpeg_sucesso_garantido(mock_subprocess, simulador_io):
    # Organizar: Retorno ideal fictício de sucesso (Exit Status = 0)
    mock_subprocess.return_value = MagicMock(returncode=0)

    # Configurações teóricas extraídas de regressão algorítmica TAL (Temporal IoU)
    inicio_corte = 25.0
    fim_corte = 40.0

    # Agir: Disparar interface externa
    simulador_io.processar_recorte_ffmpeg(
        entrada="/arquivos/sermon.webm",
        start=inicio_corte,
        end=fim_corte,
        pasta_destino="aprovados/shorts_9_16"
    )

    # Afirmar: Inspeção estrita dos argumentos e strings (garante coesão do fatiamento FFmpeg)
    mock_subprocess.assert_called_once()
    argumentos_capturados = mock_subprocess.call_args[0][0]

    # Avaliação do algoritmo de margem respiratória: o sistema de seek FFmpeg retrocede 0.3s (24.7)
    # e avança a duração compensando expansões de ambos lados
    # Duração (t) = 40.3 (fim ajustado) - 24.7 (início ajustado) = 15.6 segundos
    idx_seek = argumentos_capturados.index("-ss")
    assert float(argumentos_capturados[idx_seek + 1]) == pytest.approx(24.7, 0.01)

    idx_tempo = argumentos_capturados.index("-t")
    assert float(argumentos_capturados[idx_tempo + 1]) == pytest.approx(15.6, 0.01)


@patch("subprocess.run")
def test_falhas_fatais_isoladas_com_perdao_operacional(mock_subprocess, simulador_io):
    # Organizar: Levantar catástrofe de encerramento temporizador e travamentos transcodificadores lentos
    mock_subprocess.side_effect = subprocess.TimeoutExpired(cmd="ffmpeg", timeout=120)

    # Agir e Afirmar a tolerância encapsulada
    with pytest.raises(ErroProcessoVideo) as retentor:
        simulador_io.processar_recorte_ffmpeg(
            entrada="/arquivos/corrompido.mp3",
            start=0,
            end=10,
            pasta_destino="aprovados"
        )

    # Assegura que falha grave lança flag interno tolerante que o processador global registrará
    assert "Timeout exaurido ao invocar subprocesso de fatiamento" in str(retentor.value)
