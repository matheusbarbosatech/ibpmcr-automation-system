# -*- coding: utf-8 -*-
"""
Módulo Concurrency & Memory Safeguards — Gestão de Processos e Prevenção de Processos Órfãos
IBPM CR Automation System
"""

import os
import sys
import time
import threading
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from typing import Optional, Any

_spacy_model_global: Any = None


def init_spacy_worker(model_name: str = "pt_core_news_sm") -> None:
    """
    Função de inicialização executada uma única vez no startup de cada worker do ProcessPoolExecutor.
    """
    global _spacy_model_global
    _spacy_model_global = f"model_mock_{model_name}"


def helper_get_pid() -> int:
    """Função top-level importável para teste de worker pid."""
    return os.getpid()


def get_global_spacy_model() -> Any:
    """Retorna a instância global do spaCy pré-carregada no worker."""
    global _spacy_model_global
    return _spacy_model_global


def process_pool_with_initializer(max_workers: Optional[int] = 1) -> ProcessPoolExecutor:
    """
    Cria uma instância de ProcessPoolExecutor configurada com o initializer de retenção
    de modelo e mitigações contra vazamento de memória.
    """
    return ProcessPoolExecutor(
        max_workers=max_workers,
        initializer=init_spacy_worker,
        initargs=("pt_core_news_sm",)
    )
