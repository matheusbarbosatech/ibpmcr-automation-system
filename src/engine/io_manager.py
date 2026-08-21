# -*- coding: utf-8 -*-
"""
Módulo I/O Manager — Interceptação de Chamadas do Sistema e Fatiamento Audiovisual
IBPM CR Automation System
"""

import os
import subprocess
from pathlib import Path
from typing import Optional, List, Dict, Any


class ErroProcessoVideo(Exception):
    """Exceção customizada para falhas fatais no fatiamento FFmpeg."""
    pass


class AudioSlicerIO:
    """
    Motor de I/O para fatiamento audiovisual e busca indexada no FFmpeg.
    """

    def __init__(self, diretorio_raiz: str = "."):
        self.diretorio_raiz = Path(diretorio_raiz)

    def processar_recorte_ffmpeg(
        self,
        entrada: str,
        start: float,
        end: float,
        pasta_destino: str,
        sample_rate: int = 44100
    ) -> bool:
        """
        Executa comando FFmpeg com margem de respiro temporal de +0.3s antes e depois do corte.
        StartSeek = max(0.0, start - 0.3)
        EndSeek = end + 0.3
        Duração = EndSeek - StartSeek
        """
        start_ajustado = float(max(0.0, start - 0.3))
        end_ajustado = float(end + 0.3)
        duracao_ajustada = float(end_ajustado - start_ajustado)

        caminho_entrada = str(Path(entrada))
        pasta_out = self.diretorio_raiz / pasta_destino
        caminho_saida = str(pasta_out / f"corte_{int(start)}_{int(end)}.mp3")

        cmd = [
            "ffmpeg",
            "-y",
            "-ss", f"{start_ajustado:.1f}",
            "-i", caminho_entrada,
            "-t", f"{duracao_ajustada:.1f}",
            "-acodec", "libmp3lame",
            "-b:a", "192k",
            "-ar", str(sample_rate),
            caminho_saida
        ]

        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
                timeout=120
            )
            return True
        except subprocess.TimeoutExpired as te:
            raise ErroProcessoVideo(f"Timeout exaurido ao invocar subprocesso de fatiamento: {te}")
        except subprocess.CalledProcessError as cpe:
            raise ErroProcessoVideo(f"Erro na execução do FFmpeg (exit code {cpe.returncode}): {cpe.stderr}")
        except Exception as ex:
            raise ErroProcessoVideo(f"Falha de I/O em fatiamento audiovisual: {ex}")
