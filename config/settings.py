"""
Módulo de Configuração Global - IBPM CR Automation System (Fase 1).

Centraliza caminhos locais, credenciais de API, estrutura de banco SQLite,
armazenamento de áudios leves (64kbps) e configurações otimizadas de CPU (Faster-Whisper INT8).
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente (.env)
load_dotenv()

# Diretório Base do Projeto
BASE_DIR = Path(__file__).resolve().parent.parent

# Diretórios Principais da Fase 1
DATA_DIR = BASE_DIR / "data"
DB_DIR = DATA_DIR / "db"
JSON_DIR = DATA_DIR / "json"
AUDIO_DIR = DATA_DIR / "audio_podcasts"
REPORTS_DIR = BASE_DIR / "reports"

# Arquivos de Armazenamento Principal
DB_PATH = DB_DIR / "ibpmcr_master.db"
JSON_MASTER_PATH = JSON_DIR / "plano_mestre_ibpmcr.json"

# Garantia de criação das pastas locais da Fase 1
for d in [DATA_DIR, DB_DIR, JSON_DIR, AUDIO_DIR, REPORTS_DIR]:
    os.makedirs(d, exist_ok=True)

# Google Drive Path (no Colab ou se especificado)
DRIVE_ROOT_DEFAULT = "/content/drive/MyDrive/IBPM_CR_Cortes"
DRIVE_ROOT = os.getenv("DRIVE_MOUNT_PATH", DRIVE_ROOT_DEFAULT)

# 16 Subpastas Estruturais da IBPM CR no Google Drive
SUBFOLDERS = {
    "STATE": "estado_videos.json",
    "RECENT": "01_Mais_Recentes",
    "MOST_VIEWED": "02_Mais_Vistos",
    "HISTORY": "03_Acervo_Historico",
    "MEDIUM_TEMATIC": "04_Videos_Medios_Tematicos",
    "EBOOKS_DEVOCIONAIS": "05_Ebooks_e_Devocionais",
    "PODCASTS_AUDIO": "06_Podcasts_Audio",
    "SLIDES_ESTUDO": "07_Slides_Estudo",
    "BOLETINS_AUDIO": "08_Boletins_Audio_TTS",
    "CIFRAS_LOUVORES": "09_Cifras_e_Louvores",
    "TRADUCOES_MISSOES": "10_Traducoes_Missoes",
    "EBD_KIDS": "11_EBD_Kids",
    "ANIVERSARIANTES_CRM": "12_Aniversariantes_CRM",
    "AUDIODESCRICAO_A11Y": "13_Audiodescricao_A11y",
    "RELATORIOS_ANALYTICS": "14_Relatorios_Analytics",
    "ESCALAS_VOLUNTARIOS": "15_Escalas_Voluntarios",
    "RAG_TEOLOGICO": "16_RAG_Teologico_Exegetico",
}

THEMATIC_SUBFOLDERS = ["Oracao", "Familia", "Fe", "Libertacao"]

# YouTube API & Canal IBPM CR Config
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "AIzaSyDoJ6EifKuGj9LqO3-28EyZ7CRkDlYehgI")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UCHhLxWRcCB-xKo0ifOQ8MVQ")
YOUTUBE_CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@ibpmcr7976")

# Bot & Telegram Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8546464130:AAFBwpeGuv8Npl22o6D-npw9KMwNGIhD-W0")
TELEGRAM_PASTORAL_CHAT_ID = os.getenv("TELEGRAM_PASTORAL_CHAT_ID", "1443802359")
HUGGINGFACE_TOKEN = os.getenv("HUGGINGFACE_TOKEN", "")

# Configurações de CPU e Faster-Whisper para Execução Local Otimizada
USE_CUDA = os.getenv("USE_CUDA", "False").lower() in ("true", "1", "t")
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "small")
WHISPER_DEVICE = "cuda" if USE_CUDA else "cpu"
WHISPER_COMPUTE_TYPE = "float16" if USE_CUDA else "int8"
