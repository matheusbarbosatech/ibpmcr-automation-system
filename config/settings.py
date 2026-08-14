"""
Configurações Globais do IBPM CR Automation System (Fase 1, 2 e 3).

Define caminhos de diretórios locais/nuvem, chaves de API e constantes para
ingestão de áudio, transcrição por IA e mineração inteligente de conteúdo (Gemini 1.5 Flash / Groq LLM API).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente do arquivo .env
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# ☁️ Detecção Automática e Dinâmica do Caminho do Google Drive
env_drive_path = os.getenv("DRIVE_MOUNT_PATH", r"G:\Meu Drive\IBPM_CR_Cortes")

POSSIBLE_GDRIVE_PATHS = [
    Path(env_drive_path),
    Path(r"G:\Meu Drive\IBPM_CR_Cortes"),
    Path(r"G:\My Drive\IBPM_CR_Cortes"),
    Path(r"G:\IBPM_CR_Cortes"),
    Path(os.path.expanduser(r"~\Google Drive\IBPM_CR_Cortes")),
]

GDRIVE_BASE = None
for p in POSSIBLE_GDRIVE_PATHS:
    if p.exists():
        GDRIVE_BASE = p
        break

if not GDRIVE_BASE:
    # Se nenhuma letra G: estiver montada, força a tentativa no caminho configurado no .env
    GDRIVE_BASE = Path(env_drive_path)

USE_GDRIVE = GDRIVE_BASE.exists()

# Diretórios Principais (Com fallback inteligente no Google Drive)
DATA_DIR = BASE_DIR / "data"
DB_DIR = GDRIVE_BASE if USE_GDRIVE else (DATA_DIR / "db")
JSON_EXPORT_DIR = DATA_DIR / "json"

# Pasta de Áudio e Subpastas Unificadas da Fase 2 e 3
if USE_GDRIVE:
    AUDIO_DIR = GDRIVE_BASE / "audio_podcasts"
else:
    AUDIO_DIR = DATA_DIR / "audio_podcasts"

TRANSCRICOES_DIR = AUDIO_DIR / "transcricoes"
INSIGHTS_DIR = AUDIO_DIR / "conteudos_fase3"
REPORT_DIR = BASE_DIR / "reports"

# Garante que os diretórios existam
for path in [DATA_DIR, DB_DIR, JSON_EXPORT_DIR, AUDIO_DIR, TRANSCRICOES_DIR, INSIGHTS_DIR, REPORT_DIR]:
    try:
        path.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass

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

# Parâmetros da API Gemini LLM (Fase 3 - Nuvem AI Studio)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-1.5-flash")

# Parâmetros da API Groq Cloud (Fallback Nuvem Open-Source)
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL_NAME = os.getenv("GROQ_MODEL_NAME", "llama-3.3-70b-versatile")
GROQ_FALLBACK_MODELS = [
    "llama-3.3-70b-versatile",
    "qwen-2.5-72b-instruct",
    "deepseek-r1-distill-llama-70b",
    "mixtral-8x7b-32768"
]

# Parâmetros de Áudio
AUDIO_BITRATE = "64k"
AUDIO_CHANNELS = 1  # Mono
AUDIO_SAMPLE_RATE = "16000"

# Configurações do Faster-Whisper CPU
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "large-v3")
WHISPER_DEVICE = os.getenv("WHISPER_DEVICE", "cpu")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "int8")
