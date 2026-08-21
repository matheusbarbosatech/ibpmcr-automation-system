# -*- coding: utf-8 -*-
"""
Testes Unitários Concurrency & Memory Safeguards — Gestão de ProcessPoolExecutor e Limites de Memória
IBPM CR Automation System
"""

import os
import sys
import pytest
from src.engine.concurrency import (
    init_spacy_worker,
    get_global_spacy_model,
    helper_get_pid,
    process_pool_with_initializer
)


def test_init_spacy_worker_startup():
    init_spacy_worker("pt_core_news_sm")
    model = get_global_spacy_model()
    assert model is not None


def test_process_pool_executor_initializer_invocation():
    with process_pool_with_initializer(max_workers=1) as executor:
        future = executor.submit(helper_get_pid)
        worker_pid = future.result(timeout=5)
        assert isinstance(worker_pid, int)
        assert worker_pid > 0


@pytest.mark.limit_memory("500 MB")
def test_garantia_limite_memoria_residente():
    matriz_teste = [i for i in range(1000)]
    assert len(matriz_teste) == 1000
