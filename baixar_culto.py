"""
Script Helper de Ingestão por Link Direto do YouTube - IBPM CR Automation System.

Permite baixar o áudio leve de qualquer vídeo/culto do YouTube informando apenas a URL.
Aplica automaticamente o padrão de nomenclatura incremental do projeto:
[ID_INCREMENTAL]_[YYYY-MM-DD]_[VIDEO_ID]_[TITULO_SANITIZADO].mp3

Uso no Terminal:
    python baixar_culto.py "https://www.youtube.com/watch?v=FlqCTPRsIT4"
    python baixar_culto.py "https://youtu.be/FlqCTPRsIT4"
"""

import sys
import os
import re
import json
import argparse
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

# Suporte UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

from src.core.config import settings
from src.core.logger import get_logger
from src.core.state_manager import MasterPlanManager, sanitize_title

logger = get_logger("BaixarCultoCLI")


def extract_video_id_from_url(url: str) -> str:
    """Extrai o ID alfanumérico do vídeo do YouTube a partir da URL."""
    match = re.search(r"(?:v=|\/|be\/)([a-zA-Z0-9_-]{11})", url)
    if match:
        return match.group(1)
    return url.strip()


def get_video_metadata_ytdlp(url: str) -> Dict[str, Any]:
    """Extrai metadados do vídeo (título, data de publicação, ID) usando yt-dlp."""
    v_id = extract_video_id_from_url(url)
    full_url = f"https://www.youtube.com/watch?v={v_id}"

    if HAS_YT_DLP:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'skip_download': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(full_url, download=False)
                pub_date = info.get("upload_date", "")  # YYYYMMDD
                if len(pub_date) == 8:
                    date_str = f"{pub_date[:4]}-{pub_date[4:6]}-{pub_date[6:8]}"
                else:
                    date_str = "2026-08-14"

                return {
                    "video_id": v_id,
                    "titulo_original": info.get("title", f"Culto_{v_id}"),
                    "data_publicacao": date_str,
                    "url": full_url,
                    "duracao_segundos": int(info.get("duration", 3600))
                }
        except Exception as e:
            logger.warning("Falha ao extrair metadados via biblioteca nativa yt_dlp", error=str(e))

    return {
        "video_id": v_id,
        "titulo_original": f"Culto_{v_id}",
        "data_publicacao": "2026-08-14",
        "url": full_url,
        "duracao_segundos": 3600
    }


def download_single_sermon_mp3(youtube_url: str) -> Optional[Path]:
    """
    Realiza o download do áudio MP3 no padrão exato do repositório IBPM CR.
    """
    state_mgr = MasterPlanManager()
    audio_dir = Path("data/audio_podcasts")
    audio_dir.mkdir(parents=True, exist_ok=True)

    v_id = extract_video_id_from_url(youtube_url)
    logger.info("📡 Analisando link do YouTube...", url=youtube_url, video_id=v_id)

    # 1. Extração de metadados
    meta = get_video_metadata_ytdlp(youtube_url)
    title_orig = meta["titulo_original"]
    date_str = meta["data_publicacao"]
    clean_t = sanitize_title(title_orig)

    # 2. Determinação do índice incremental via consulta SQLite
    idx = 452
    existing_idx = None

    try:
        with state_mgr._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT indice_sequencial FROM videos WHERE video_id = ?", (v_id,))
            row = cursor.fetchone()
            if row and row[0]:
                existing_idx = row[0]
            else:
                cursor.execute("SELECT COUNT(*) FROM videos")
                count_total = cursor.fetchone()[0]
                idx = count_total + 1 if count_total > 0 else 452
    except Exception:
        pass

    if existing_idx:
        idx = existing_idx

    target_filename = f"{idx:03d}_{date_str}_{v_id}_{clean_t}.mp3"
    target_filepath = audio_dir / target_filename

    # 3. Checa se o arquivo já foi baixado previamente
    if target_filepath.exists() and target_filepath.stat().st_size > 10000:
        logger.info("✨ Arquivo de áudio já existe no computador!", file=str(target_filepath.resolve()))
        state_mgr.mark_audio_downloaded(v_id, str(target_filepath))
        return target_filepath.resolve()

    filename_no_ext = f"{idx:03d}_{date_str}_{v_id}_{clean_t}"
    full_url = meta["url"]

    logger.info(
        "📥 Efetuando download do áudio MP3 (128k)...",
        idx=idx,
        date=date_str,
        video_id=v_id,
        title=title_orig
    )

    # 4. Execução do Download via yt-dlp com bypass de 403 Forbidden
    if HAS_YT_DLP:
        ydl_opts = {
            'format': 'ba/ba*/bestaudio/best',
            'outtmpl': str(audio_dir / f"{filename_no_ext}.%(ext)s"),
            'quiet': True,
            'no_warnings': True,
            'extractor_args': {
                'youtube': {
                    'player_client': ['android', 'web']
                }
            },
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        }
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([full_url])

            # Localiza o arquivo gerado
            for fname in os.listdir(audio_dir):
                if v_id in fname and not fname.endswith(".part"):
                    full_p = (audio_dir / fname).resolve()
                    if full_p.stat().st_size > 10000:
                        video_data = {
                            "video_id": v_id,
                            "titulo_original": title_orig,
                            "data_publicacao": date_str,
                            "duracao_segundos": meta["duracao_segundos"],
                            "url": full_url,
                            "indice_sequencial": idx,
                            "titulo_sanitizado": clean_t,
                            "nome_arquivo_mp3": full_p.name
                        }
                        state_mgr.save_video_metadata(video_data)
                        state_mgr.mark_audio_downloaded(v_id, str(full_p))
                        
                        logger.info(
                            "🎉 Download concluído com sucesso!",
                            file_name=full_p.name,
                            file_path=str(full_p),
                            size_mb=round(full_p.stat().st_size / (1024 * 1024), 2)
                        )
                        return full_p
        except Exception as e:
            logger.warning("Falha no download via biblioteca nativa yt_dlp. Tentando subprocesso CLI...", error=str(e))

    # Fallback via Subprocess CLI
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "--format", "ba/ba*/bestaudio/best",
        "--extractor-args", "youtube:player_client=android,web",
        "--output", str(audio_dir / f"{filename_no_ext}.%(ext)s"),
        full_url
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        for fname in os.listdir(audio_dir):
            if v_id in fname and not fname.endswith(".part"):
                full_p = (audio_dir / fname).resolve()
                if full_p.stat().st_size > 10000:
                    video_data = {
                        "video_id": v_id,
                        "titulo_original": title_orig,
                        "data_publicacao": date_str,
                        "duracao_segundos": meta["duracao_segundos"],
                        "url": full_url,
                        "indice_sequencial": idx,
                        "titulo_sanitizado": clean_t,
                        "nome_arquivo_mp3": full_p.name
                    }
                    state_mgr.save_video_metadata(video_data)
                    state_mgr.mark_audio_downloaded(v_id, str(full_p))

                    logger.info(
                        "🎉 Download concluído via subprocess CLI!",
                        file_name=full_p.name,
                        file_path=str(full_p)
                    )
                    return full_p
    except subprocess.CalledProcessError as e:
        logger.error("Falha no download do áudio via yt-dlp", error=e.stderr)
        raise RuntimeError(f"Erro no download: {e.stderr}")

    return None


def main():
    parser = argparse.ArgumentParser(description="Helper de Ingestão por Link de Vídeo do YouTube (IBPM CR)")
    parser.add_argument("url", type=str, help="URL ou ID do vídeo do YouTube (ex: https://www.youtube.com/watch?v=...)")
    args = parser.parse_args()

    result_path = download_single_sermon_mp3(args.url)
    if result_path:
        print("\n===========================================================================")
        print(" ✅ PROCESSO CONCLUÍDO COM SUCESSO!")
        print(f" 📂 Arquivo MP3 Salvo: {result_path}")
        print(" 💡 Dica: Agora você pode rodar 'python processar_audios_locais_gemini.py'")
        print("===========================================================================\n")


if __name__ == "__main__":
    main()
