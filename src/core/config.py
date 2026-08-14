"""
Módulo de Configuração Global do IBPM CR Automation System.

Gerencia a leitura, validação e injeção de variáveis de ambiente (.env)
utilizando Pydantic Settings V2 com suporte para caminhos no host Windows/Linux,
credenciais de APIs (Google, Meta), brokers (Celery/RabbitMQ/Redis) e binários locais (FFmpeg/Rclone).
"""

import os
from pathlib import Path
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    """
    Configuração Centralizada e Tipada da Aplicação.
    """
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False
    )

    # -------------------------------------------------------------------------
    # 1. CORE APPLICATION CONFIGURATION
    # -------------------------------------------------------------------------
    ENVIRONMENT: str = Field(default="development", description="Ambiente de execução (development, staging, production)")
    LOG_LEVEL: str = Field(default="INFO", description="Nível de log (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
    APP_TIMEZONE: str = Field(default="America/Sao_Paulo", description="Fuso horário oficial da aplicação")

    # -------------------------------------------------------------------------
    # 2. BROKER & BACKEND CONFIGURATION (REDIS / RABBITMQ)
    # -------------------------------------------------------------------------
    CELERY_BROKER_URL: str = Field(
        default="amqp://admin:admin_password@localhost:5672//",
        description="URL de conexão com o broker RabbitMQ"
    )
    CELERY_RESULT_BACKEND: str = Field(
        default="redis://:redis_password@localhost:6379/0",
        description="URL de conexão com o backend de resultados Redis"
    )

    # -------------------------------------------------------------------------
    # 3. DATABASE CONFIGURATION (SQLITE / SQLALCHEMY)
    # -------------------------------------------------------------------------
    DATABASE_URL: str = Field(
        default="sqlite:///./data/database/ibpm_core.db",
        description="URL de conexão com o banco de dados SQLite em modo WAL"
    )

    # -------------------------------------------------------------------------
    # 4. GOOGLE AI & APIS (GEMINI, YOUTUBE, DRIVE)
    # -------------------------------------------------------------------------
    GOOGLE_API_KEY: str = Field(default="", description="Chave da API do Google Cloud")
    GEMINI_API_KEY: str = Field(default="", description="Chave da API do Google Gemini AI Studio")
    GOOGLE_GEMINI_MODEL: str = Field(default="gemini-flash-latest", description="Modelo padrão do Gemini")
    GROQ_API_KEY: str = Field(default="", description="Chave da API Groq Cloud (Whisper Large V3)")
    
    YOUTUBE_API_KEY: str = Field(default="", description="Chave pública da API do YouTube Data v3")
    YOUTUBE_CHANNEL_ID: str = Field(default="UCHhLxWRcCB-xKo0ifOQ8MVQ", description="ID do canal oficial IBPM CR")
    YOUTUBE_CHANNEL_HANDLE: str = Field(default="@ibpmcr7976", description="Handle do canal oficial IBPM CR")
    YOUTUBE_UPLOADS_PLAYLIST: str = Field(default="UUHhLxWRcCB-xKo0ifOQ8MVQ", description="ID da playlist de uploads do canal")
    YOUTUBE_CLIENT_SECRETS_FILE: str = Field(default="./credentials/client_secret_google.json", description="OAuth2 client secrets")
    YOUTUBE_TOKEN_PATH: str = Field(default="./credentials/youtube_token.pickle", description="Caminho do token OAuth2 persistido")
    GOOGLE_DRIVE_FOLDER_ID: str = Field(default="", description="ID da pasta raiz no Google Drive")

    # -------------------------------------------------------------------------
    # 5. META / INSTAGRAM GRAPH API
    # -------------------------------------------------------------------------
    INSTAGRAM_ACCESS_TOKEN: str = Field(default="", description="User Access Token para Instagram Graph API")
    INSTAGRAM_ACCOUNT_ID: str = Field(default="", description="ID da conta profissional do Instagram IBPM CR")

    # -------------------------------------------------------------------------
    # 6. LOCAL BINARIES PATHS (HOST WINDOWS/LINUX)
    # -------------------------------------------------------------------------
    FFMPEG_BINARY_PATH: str = Field(default="ffmpeg", description="Caminho absoluto ou comando para o executável do FFmpeg")
    FFPROBE_BINARY_PATH: str = Field(default="ffprobe", description="Caminho absoluto ou comando para o executável do FFprobe")
    RCLONE_CONFIG_PATH: str = Field(default="", description="Caminho para o arquivo rclone.conf")
    RCLONE_REMOTE_NAME: str = Field(default="meudrive", description="Nome do remote configurado no Rclone")

    # -------------------------------------------------------------------------
    # 7. DIRETORES E ARMAZENAMENTO DE ARTEFATOS
    # -------------------------------------------------------------------------
    DATA_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data")
    CACHE_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data" / "cache")
    OUTPUT_DIR: Path = Field(default_factory=lambda: BASE_DIR / "data" / "output")
    LOGS_DIR: Path = Field(default_factory=lambda: BASE_DIR / "logs")

    def create_required_directories(self) -> None:
        """Cria as pastas locais necessárias no disco caso não existam."""
        self.DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.CACHE_DIR.mkdir(parents=True, exist_ok=True)
        self.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        self.LOGS_DIR.mkdir(parents=True, exist_ok=True)


# Instância Global de Configuração
settings = Settings()
settings.create_required_directories()
