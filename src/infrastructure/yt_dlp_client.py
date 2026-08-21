"""
Cliente de Ingestão e Download Cirúrgico com yt-dlp - IBPM CR Automation System.

Utiliza a biblioteca yt-dlp nativa em Python (ou via subprocesso) para realizar o download
cirúrgico de trechos de vídeos do YouTube via requisições HTTP de intervalo (Range Requests),
evitando o download desnecessário de arquivos integrais de 2 horas.
"""

import sys
import os
import re
import json
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

        cookies_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
        cookies_arg = ["--cookies", str(cookies_file)] if cookies_file.exists() else []

        format_str_4k = "bestvideo[height<=2160]+bestaudio/bestvideo+bestaudio/best"
        import shutil
        ffmpeg_exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or settings.FFMPEG_BINARY_PATH
        if ffmpeg_exe and Path(ffmpeg_exe).exists():
            ffmpeg_location_arg = str(Path(ffmpeg_exe).resolve())
        else:
            ffmpeg_location_arg = "ffmpeg"

        node_exe = shutil.which("node") or shutil.which("node.exe") or r"C:\Program Files\nodejs\node.exe"

        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--no-progress",
            "--quiet",
            "--concurrent-fragments", "8",
            "--js-runtimes", f"node:{node_exe}",
            "--remote-components", "ejs:github",
            "--download-sections", section_str,
            "-f", format_str_4k,
            "--ffmpeg-location", ffmpeg_location_arg,
            "--merge-output-format", "mp4",
            "--output", f"{filename_no_ext}.%(ext)s",
        ] + cookies_arg + [video_url]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            for ext in [".mp4", ".mkv", ".webm"]:
                candidate = Path(f"{filename_no_ext}{ext}")
                if candidate.exists() and candidate.stat().st_size > 10000:
                    logger.info("Download cirúrgico 4K concluído com sucesso", job_id=job_id, file=str(candidate))
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
        parts = output_path.stem.split("_")
        yt_id_match = next((p for p in parts if len(p) == 11 and re.match(r'^[a-zA-Z0-9_-]{11}$', p)), output_path.stem)

        # Se o vídeo já foi baixado completamente (> 10MB), reutiliza do cache
        if output_path.exists() and output_path.stat().st_size > 10_000_000:
            logger.info(f"✅ Vídeo completo 4K/HD já existe em cache local: {output_path} ({output_path.stat().st_size / (1024*1024):.1f} MB)", job_id=job_id)
            return output_path

        # Limpa rigorosamente quaisquer arquivos parciais ou temporários (.f315.webm, .f401.mp4, .part, etc)
        for item in list(output_path.parent.glob(f"*{yt_id_match}*")):
            if item.resolve() != output_path.resolve():
                try:
                    item.unlink()
                except Exception:
                    pass

        logger.info(f"📥 Disparando download do vídeo completo em 4K/1080p HD (Qualidade Máxima): {video_url}", job_id=job_id)

        import shutil
        ffmpeg_exe = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe") or settings.FFMPEG_BINARY_PATH
        if ffmpeg_exe and Path(ffmpeg_exe).exists():
            ffmpeg_location_arg = str(Path(ffmpeg_exe).resolve())
        else:
            ffmpeg_location_arg = "ffmpeg"

        node_exe = shutil.which("node") or shutil.which("node.exe") or r"C:\Program Files\nodejs\node.exe"

        cookies_file = Path(__file__).resolve().parent.parent.parent / "cookies.txt"
        cookies_arg = ["--cookies", str(cookies_file)] if cookies_file.exists() else []

        # Seletor universal de MÁXIMA QUALIDADE ABSOLUTA 4K -> 2K -> 1080p60 -> Best
        format_str = "315+140/401+140/308+140/400+140/299+140/399+140/137+140/bestvideo[height>=2160]+bestaudio/bestvideo[height>=1440]+bestaudio/bestvideo[height>=1080]+bestaudio/best"

        # Dispara via subprocess CLI (evita fallbacks do módulo Python)
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--extractor-args", "youtube:player_client=android,web",
            "--js-runtimes", f"node:{node_exe}",
            "--remote-components", "ejs:github",
            "--no-cache-dir",
            "-f", format_str,
            "--ffmpeg-location", ffmpeg_location_arg,
            "--merge-output-format", "mp4",
            "--no-continue",
            "--force-overwrites",
            "--postprocessor-args", "ffmpeg:-async 1 -vsync cfr",
            "-o", f"{filename_no_ext}.%(ext)s",
        ] + cookies_arg + [video_url]



        logger.info(f"⚡ Baixando stream 4K/2K nativa do YouTube via CLI...", job_id=job_id)
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            # Limpa parciais em caso de erro para não travar os próximos vídeos
            for item in list(output_path.parent.glob(f"*{yt_id_match}*")):
                if item.resolve() != output_path.resolve():
                    try:
                        item.unlink()
                    except Exception:
                        pass
            logger.error(f"Falha no download 4K nativo: {res.stderr}", job_id=job_id)
            raise RuntimeError(f"Erro ao baixar vídeo completo na melhor qualidade: {res.stderr}")

        for ext in [".mp4", ".mkv", ".webm"]:
            candidate = Path(f"{filename_no_ext}{ext}")
            if candidate.exists() and candidate.stat().st_size > 1_000_000:
                logger.info("✅ Download de alta qualidade 4K/2K concluído com sucesso via CLI", job_id=job_id, file=str(candidate))
                return candidate

        # Fallback yt_dlp nativo

        if HAS_YT_DLP:
            ydl_opts = {
                'format': format_str,
                'outtmpl': f"{filename_no_ext}.%(ext)s",
                'merge_output_format': 'mp4',
                'ffmpeg_location': str(ffmpeg_exe),
                'quiet': False,
                'no_warnings': True,
                'format_sort': ['res:2160', 'res:1440', 'res:1080', 'fps:60', 'vbr', 'codec:vp9', 'codec:av01', 'aext:m4a'],
                'postprocessor_args': {
                    'ffmpeg': ['-async', '1', '-vsync', 'cfr']
                }
            }


            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([video_url])

                for ext in [".mp4", ".mkv", ".webm"]:
                    candidate = Path(f"{filename_no_ext}{ext}")
                    if candidate.exists() and candidate.stat().st_size > 50000:
                        logger.info("✅ Download de alta qualidade 4K/2K concluído via módulo Python", job_id=job_id, file=str(candidate))
                        return candidate
            except Exception as e:
                logger.error(f"Falha no download 4K nativo: {e}")




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


