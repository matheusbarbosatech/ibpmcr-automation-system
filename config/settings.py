"""
Módulo de Configuração Global - IBPM CR Automation System.

Este módulo centraliza todas as variáveis de ambiente, caminhos de diretórios do Google Drive
e configurações de execução do sistema para o ecossistema IBPM CR.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis do arquivo .env caso exista
load_dotenv()

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent

# Google Drive Root Path (no Google Colab)
DRIVE_ROOT_DEFAULT = "/content/drive/MyDrive/IBPM_CR_Cortes"
DRIVE_ROOT = os.getenv("DRIVE_MOUNT_PATH", DRIVE_ROOT_DEFAULT)

# Local Storage Path (para execuções locais / testes sem Colab)
LOCAL_STORAGE = os.getenv("LOCAL_STORAGE_PATH", str(BASE_DIR / "data_storage"))

# Seleção do diretório ativo de saída
OUTPUT_BASE_DIR = DRIVE_ROOT if os.path.exists("/content/drive") else LOCAL_STORAGE

# Estrutura das 16 Subpastas do Ecossistema
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

# Subpastas Temáticas para Vídeos Médios 16:9
THEMATIC_SUBFOLDERS = ["Oracao", "Familia", "Fe", "Libertacao"]

# YouTube API Config
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")
YOUTUBE_CHANNEL_ID = os.getenv("YOUTUBE_CHANNEL_ID", "UC_ibpmcr_id")
YOUTUBE_CHANNEL_HANDLE = os.getenv("YOUTUBE_CHANNEL_HANDLE", "@ibpmcr7976")

# Bot & Webhook Credentials
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_PASTORAL_CHAT_ID = os.getenv("TELEGRAM_PASTORAL_CHAT_ID", "")

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_WHATSAPP_NUMBER = os.getenv("TWILIO_WHATSAPP_NUMBER", "whatsapp:+14155238886")

# AI & Processing Specs
USE_CUDA = os.getenv("USE_CUDA", "True").lower() == "true"
WHISPER_MODEL_SIZE = os.getenv("WHISPER_MODEL_SIZE", "medium")
SPACY_MODEL = os.getenv("SPACY_MODEL", "pt_core_news_sm")

def get_folder_path(key: str) -> str:
    """
    Retorna o caminho absoluto de uma subpasta do ecossistema.

    :param key: Chave correspondente no dicionário SUBFOLDERS.
    :return: Caminho em formato string.
    """
    folder_name = SUBFOLDERS.get(key, "")
    return os.path.join(OUTPUT_BASE_DIR, folder_name)
