# -*- coding: utf-8 -*-
"""
Engine de Processamento e Controle de Qualidade Automático (AQC)
IBPM CR Automation System
"""

from .aqc_nlp import MotorAQC, ValidadorSentido, TextCohesionNLP
from .aqc_dsp import AnalisadorDSP, MotorCadencia
from .io_manager import AudioSlicerIO, ErroProcessoVideo
from .tal_metrics import (
    calcular_tIoU,
    emparelhamento_algoritmo_hungaro,
    calcular_metricas_tal,
    MétricasTAL
)
from .batch_regression import RegressãoBatchRunner
from .concurrency import init_spacy_worker, process_pool_with_initializer

__all__ = [
    "MotorAQC",
    "ValidadorSentido",
    "TextCohesionNLP",
    "AnalisadorDSP",
    "MotorCadencia",
    "AudioSlicerIO",
    "ErroProcessoVideo",
    "calcular_tIoU",
    "emparelhamento_algoritmo_hungaro",
    "calcular_metricas_tal",
    "MétricasTAL",
    "RegressãoBatchRunner",
    "init_spacy_worker",
    "process_pool_with_initializer",
]
