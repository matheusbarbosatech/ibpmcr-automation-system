"""
Configurações Globais do IBPM CR Automation System (Fase 1 - Etapa 1 & 2).

Define caminhos de diretórios locais, chaves de API e constantes para o download
organizado e a transcrição sequencial por IA dos cultos do canal @ibpmcr7976.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Diretórios Principais
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
JSON_EXPORT_DIR = DATA_DIR / "json"
AUDIO_DIR = DATA_DIR / "audio_podcasts"
REPORT_DIR = BASE_DIR / "reports"

# Garante que os diretórios existam
for path in [DATA_DIR, DB_DIR, JSON_EXPORT_DIR, AUDIO_DIR, REPORT_DIR]:
    path.mkdir(parents=True, exist_ok=True)

# Caminhos de Arquivos de Persistência
DB_PATH = DB_DIR / "ibpmcr_master.db"
JSON_MASTER_PATH = JSON_EXPORT_DIR / "plano_mestre_ibpmcr.json"
PDF_REPORT_PATH = REPORT_DIR / "relatorio_acervo_ibpmcr.pdf"
HTML_REPORT_PATH = REPORT_DIR / "relatorio_acervo_ibpmcr.html"
READABLE_PDF_PATH = BASE_DIR / "PLANO_MESTRE_IBPMCR_COMPLETO.pdf"

# Configurações do YouTube
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCHhLxWRcCB-xKo0ifOQ8MVQ")
YOUTUBE_CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@ibpmcr7976")
YOUTUBE_UPLOADS_PLAYLIST = "UUHhLxWRcCB-xKo0ifOQ8MVQ"

# Parâmetros de Áudio (MP3 Leve mono a 64kbps 16kHz)
AUDIO_BITRATE = "64k"
AUDIO_CHANNELS = 1  # Mono
AUDIO_SAMPLE_RATE = "16000"

# Configurações do Faster-Whisper CPU
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "base")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
