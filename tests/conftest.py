# -*- coding: utf-8 -*-
"""
Pytest Conftest — Fixtures Determinísticas e Injeção de Mocks para Suíte AQC
IBPM CR Automation System
"""

import sys
import os
from pathlib import Path

# Garantir que a raiz do repositório está no sys.path ANTES de qualquer importação de src
BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

import pytest
from unittest.mock import MagicMock
from src.engine.io_manager import AudioSlicerIO


@pytest.fixture
def mock_spacy_doc_factory():
    """
    Fixture de injeção contornando o custo estrutural da instância spaCy.
    Cria objetos spacy.tokens.Doc sintéticos com tensores falsos e marcadores morfológicos.
    """
    def _create_mock_doc(tokens_data):
        doc = MagicMock()
        tokens = []

        for item in tokens_data:
            if len(item) == 3:
                text, pos, dep = item
            else:
                text, pos = item[0], item[1]
                dep = "ROOT"

            token = MagicMock()
            token.text = text
            token.pos_ = pos
            token.dep_ = dep
            tokens.append(token)

        doc.__iter__.return_value = iter(tokens)
        doc.__getitem__.side_effect = lambda idx: tokens[idx]
        doc.__len__.return_value = len(tokens)
        return doc

    return _create_mock_doc


@pytest.fixture
def simulador_io():
    """Fixture que provê instância do fatiador AudioSlicerIO para ambiente simulado."""
    return AudioSlicerIO(diretorio_raiz="/acervo/testes")
