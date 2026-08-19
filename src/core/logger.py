"""
Módulo de Telemetria e JSON Logging Estruturado para o IBPM CR Automation System.

Configura a biblioteca 'structlog' em conformidade com as especificações de observabilidade
para gerar logs em formato JSON padronizado (ISO 8601, job_id, level, module_source),
redirecionando a saída para stdout e para arquivos rotativos no disco.
"""

import sys
import logging
from pathlib import Path
from typing import Any, Dict

try:
    # pyrefly: ignore [missing-import]
    import structlog
    HAS_STRUCTLOG = True
except ImportError:
    HAS_STRUCTLOG = False

try:
    from src.core.config import settings
    LOGS_DIR = settings.LOGS_DIR
    LOG_LEVEL = settings.LOG_LEVEL
except Exception:
    LOGS_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "logs"
    LOG_LEVEL = "INFO"


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
    Inicializa e parametriza o motor de logging.
    """
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    app_log_file = LOGS_DIR / "app.log"
    error_log_file = LOGS_DIR / "error.log"

    if HAS_STRUCTLOG:
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

        structlog.configure(
            processors=shared_processors + [
                structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
            ],
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )

        json_formatter = structlog.stdlib.ProcessorFormatter(
            foreign_pre_chain=shared_processors,
            processor=structlog.processors.JSONRenderer(ensure_ascii=False),
        )

        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(json_formatter)

        file_handler = logging.FileHandler(app_log_file, encoding="utf-8")
        file_handler.setFormatter(json_formatter)

        error_file_handler = logging.FileHandler(error_log_file, encoding="utf-8")
        error_file_handler.setLevel(logging.ERROR)
        error_file_handler.setFormatter(json_formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, LOG_LEVEL.upper(), logging.INFO))
        root_logger.handlers = [console_handler, file_handler, error_file_handler]
    else:
        logging.basicConfig(
            level=getattr(logging, LOG_LEVEL.upper(), logging.INFO),
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        )


setup_logger()


class SafeLoggerWrapper:
    """
    Wrapper seguro para logging.Logger da biblioteca padrão do Python,
    permitindo kwargs arbitrários (job_id, path, cut_id, etc) sem quebrar chamadas.
    """
    def __init__(self, logger: logging.Logger):
        self._logger = logger

    def _format_msg(self, msg: Any, kwargs: Dict[str, Any]) -> str:
        if not kwargs:
            return str(msg)
        extras = " | " + " ".join(f"{k}={v}" for k, v in kwargs.items())
        return f"{msg}{extras}"

    def info(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.info(self._format_msg(msg, kwargs), *args)

    def debug(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.debug(self._format_msg(msg, kwargs), *args)

    def warning(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.warning(self._format_msg(msg, kwargs), *args)

    def error(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.error(self._format_msg(msg, kwargs), *args)

    def exception(self, msg: Any, *args: Any, **kwargs: Any) -> None:
        self._logger.exception(self._format_msg(msg, kwargs), *args)


def get_logger(name: str = "ibpm_automation") -> Any:
    """
    Retorna uma instância configurada do logger (structlog ou SafeLoggerWrapper).
    """
    if HAS_STRUCTLOG:
        return structlog.get_logger(name)
    return SafeLoggerWrapper(logging.getLogger(name))


