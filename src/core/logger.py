"""
Módulo de Telemetria e JSON Logging Estruturado para o IBPM CR Automation System.

Configura a biblioteca 'structlog' em conformidade com as especificações de observabilidade
para gerar logs em formato JSON padronizado (ISO 8601, job_id, level, module_source),
redirecionando a saída para stdout e para arquivos rotativos no disco.
"""

import sys
import logging
import structlog
from pathlib import Path
from typing import Any, Dict

from src.core.config import settings


def add_correlation_fields(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """
    Injeta campos de correlação e telemetria padrão nos eventos de log caso não estejam presentes.
    """
    if "job_id" not in event_dict:
        event_dict["job_id"] = "system_global"
    if "module_source" not in event_dict:
        frame = sys._getframe(4)
        module = frame.f_globals.get("__name__", "unknown") if frame else "unknown"
        event_dict["module_source"] = module
    return event_dict


def setup_logger() -> None:
    """
    Inicializa e parametriza o motor de logging estruturado (structlog + stdlib logging).
    """
    settings.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    app_log_file = settings.LOGS_DIR / "app.log"
    error_log_file = settings.LOGS_DIR / "error.log"

    # Processadores compartilhados do Structlog
    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        add_correlation_fields,
    ]

    # Configura o structlog para atuar em sintonia com o stdlib logging
    structlog.configure(
        processors=shared_processors + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Formatador JSON para o stdlib logging
    json_formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processor=structlog.processors.JSONRenderer(ensure_ascii=False),
    )

    # Handler do Console (stdout)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(json_formatter)

    # Handler de Arquivo Geral (app.log)
    file_handler = logging.FileHandler(app_log_file, encoding="utf-8")
    file_handler.setFormatter(json_formatter)

    # Handler de Arquivo de Erros (error.log)
    error_file_handler = logging.FileHandler(error_log_file, encoding="utf-8")
    error_file_handler.setLevel(logging.ERROR)
    error_file_handler.setFormatter(json_formatter)

    # Configura o Logger Raiz do Python
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO))
    root_logger.handlers = [console_handler, file_handler, error_file_handler]

    # Silencia ou ajusta verborragia de bibliotecas de terceiros
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("googleapiclient").setLevel(logging.WARNING)
    logging.getLogger("filelock").setLevel(logging.WARNING)


# Executa a configuração ao importar o módulo
setup_logger()

def get_logger(name: str = "ibpm_automation") -> structlog.BoundLogger:
    """
    Retorna uma instância configurada do bound logger do structlog.
    """
    return structlog.get_logger(name)
