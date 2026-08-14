"""
Orquestrador Celery e Topologia de Filas - IBPM CR Automation System.

Configura o motor Celery com roteamento estrito entre filas de GPU (inferência de IA)
e filas de CPU (renderização e I/O), aplicando políticas de contenção de memória
anti-OOM (worker_prefetch_multiplier=1, worker_max_tasks_per_child=1, task_acks_late=True).
"""

from celery import Celery
from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("CeleryApp")

# Inicialização da Aplicação Celery
celery_app = Celery(
    "ibpm_automation",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["src.tasks.gpu_tasks", "src.tasks.cpu_tasks"]
)

# Configuração Avançada de Roteamento e Prevenção Anti-OOM
celery_app.conf.update(
    # Fuso Horário
    timezone=settings.APP_TIMEZONE,
    enable_utc=True,

    # Roteamento Estrito de Tarefas por Fila
    task_routes={
        "src.tasks.gpu_tasks.*": {"queue": "gpu_queue"},
        "src.tasks.cpu_tasks.*": {"queue": "cpu_queue"},
    },

    # Prevenção Anti-OOM (Out-Of-Memory) em Trabalhos de IA/GPU
    worker_prefetch_multiplier=1,      # Impede reserva desnecessária de tarefas na RAM do worker
    worker_max_tasks_per_child=1,       # Recicla o processo filho do Celery a cada tarefa concluída (limpa VRAM)
    task_acks_late=True,                # Confirmação tardia (somente após conclusão com sucesso)
    task_reject_on_worker_lost=True,    # Reenfileira a tarefa se o worker for morto abruptamente

    # Serialização
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Expiração de Resultados (24 horas)
    result_expires=86400,
)

logger.info(
    "Instância Celery inicializada com sucesso",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    prefetch_multiplier=1,
    max_tasks_per_child=1
)
