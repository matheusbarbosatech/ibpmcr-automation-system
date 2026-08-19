"""
Cliente de Ingestão e Download Cirúrgico com yt-dlp - IBPM CR Automation System.

Utiliza a biblioteca yt-dlp nativa em Python (ou via subprocesso) para realizar o download
cirúrgico de trechos de vídeos do YouTube via requisições HTTP de intervalo (Range Requests),
evitando o download desnecessário de arquivos integrais de 2 horas.
"""

import json
import sys
import os
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("YTDLPClient")


class YTDLPClient:
    """
    Sniper de Ingestão especialista em downloads cirúrgicos por intervalo de tempo.
    """

    def __init__(self):
        logger.info("YTDLPClient inicializado.", has_native_lib=HAS_YT_DLP)

    def download_surgical_cut(
        self,
        video_url: str,
        start_sec: float,
        end_sec: float,
        output_path: Path,
        margin_sec: float = 2.0,
        job_id: str = "job_surgical_cut"
    ) -> Path:
        """
        Baixa APENAS o intervalo de segundos solicitado (com margem de segurança),
        economizando gigabytes de banda e acelerando o pipeline de edição.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Aplica margem de segurança de 2s antes e depois do trecho
        start_m = max(0.0, start_sec - margin_sec)
        end_m = end_sec + margin_sec
        section_str = f"*{start_m:.1f}-{end_m:.1f}"

        logger.info(
            "Disparando download cirúrgico do YouTube",
            job_id=job_id,
            url=video_url,
            section=section_str,
            output_file=output_path.name
        )

        filename_no_ext = str(output_path.with_suffix(""))

        # Estratégia 1: Uso da biblioteca nativa Python yt_dlp
        if HAS_YT_DLP:
            ydl_opts = {
                'format': 'bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best',
                'outtmpl': f"{filename_no_ext}.%(ext)s",
                'download_ranges': yt_dlp.utils.download_range_func(None, [(start_m, end_m)]),
                'force_keyframes_at_cuts': True,
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
                    ydl.download([video_url])

                # Localiza o arquivo baixado
                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = Path(f"{filename_no_ext}{ext}")
                    if candidate.exists() and candidate.stat().st_size > 10000:
                        logger.info("Download cirúrgico concluído via biblioteca nativa", job_id=job_id, file=str(candidate))
                        return candidate
            except Exception as e:
                logger.warning("Falha na execução nativa do yt_dlp. Tentando fallback via subprocesso.", error=str(e))

        # Estratégia 2: Fallback via Subprocess CLI do yt-dlp
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--download-sections", section_str,
            "--format", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
            "--force-keyframes-at-cuts",
            "--extractor-args", "youtube:player_client=android,web",
            "--output", f"{filename_no_ext}.%(ext)s",
            video_url
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for ext in [".mp4", ".mkv", ".webm"]:
                candidate = Path(f"{filename_no_ext}{ext}")
                if candidate.exists() and candidate.stat().st_size > 10000:
                    logger.info("Download cirúrgico concluído via subprocess CLI", job_id=job_id, file=str(candidate))
                    return candidate

            raise FileNotFoundError(f"Arquivo resultante do download cirúrgico não foi encontrado em {output_path}")

        except subprocess.CalledProcessError as e:
            logger.error("Falha no download cirúrgico via subprocess CLI", job_id=job_id, stderr=e.stderr)
            raise RuntimeError(f"Erro no yt-dlp: {e.stderr}")

    def download_full_video_best_quality(self, video_url: str, output_path: Path, job_id: str = "job_full_download") -> Path:
        """
        Baixa o VÍDEO COMPLETO na MELHOR QUALIDADE POSSÍVEL (1080p / 4K MP4) unificando vídeo e áudio.
        Estratégia B: Baixa 1x e permite cortes locais instantâneos ilimitados com zero consumo de rede.
        """
        output_path.parent.mkdir(parents=True, exist_ok=True)
        filename_no_ext = str(output_path.with_suffix(""))

        logger.info(f"📥 Disparando download do vídeo MP4 completo na MELHOR QUALIDADE: {video_url}", job_id=job_id)

        format_str = "bestvideo[ext=mp4]+bestaudio[ext=m4a]/bestvideo+bestaudio/best"

        if HAS_YT_DLP:
            ydl_opts = {
                'format': format_str,
                'outtmpl': f"{filename_no_ext}.%(ext)s",
                'merge_output_format': 'mp4',
                'quiet': False,
                'no_warnings': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = Path(f"{filename_no_ext}{ext}")
                    if candidate.exists() and candidate.stat().st_size > 50000:
                        logger.info("✅ Download de alta qualidade concluído com sucesso", job_id=job_id, file=str(candidate))
                        return candidate
            except Exception as e:
                logger.warning(f"Falha yt_dlp nativo: {e}. Tentando fallback subprocess CLI...")

        # Subprocess CLI fallback
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-f", format_str,
            "--merge-output-format", "mp4",
            "-o", f"{filename_no_ext}.%(ext)s",
            video_url
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        for ext in [".mp4", ".mkv", ".webm"]:
            candidate = Path(f"{filename_no_ext}{ext}")
            if candidate.exists() and candidate.stat().st_size > 50000:
                logger.info("✅ Download de alta qualidade concluído via CLI", job_id=job_id, file=str(candidate))
                return candidate

        raise RuntimeError(f"Erro ao baixar vídeo completo na melhor qualidade: {res.stderr}")

    def get_video_metadata(self, video_url: str) -> Dict[str, Any]:
        """
        Obtém metadados técnicos completos de um vídeo do YouTube via yt-dlp CLI dump-json.
        """
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--dump-json",
            "--skip-download",
            "--no-warnings",
            video_url
        ]
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            return json.loads(res.stdout)
        except Exception as e:
            logger.warning(f"Falha ao obter metadados via CLI: {e}. Tentando biblioteca nativa...")

        if HAS_YT_DLP:
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'extractor_args': {'youtube': {'player_client': ['android', 'web']}}
            }
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(video_url, download=False)
                    return info or {}
            except Exception as err:
                logger.error(f"Falha ao extrair metadados nativos: {err}")

        return {"error": "Não foi possível obter metadados"}


