"""
Módulo de Filtro de Qualidade de Mídia - IBPM CR Automation System.

Analisa tecnicamente vídeos do YouTube sem realizar o download do arquivo,
avaliando resolução, taxa de quadros (FPS), codecs e bitrates para qualificar
quais conteúdos têm nível profissional para cortes nas redes sociais.
"""

import os
import csv
import json
import sys
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.infrastructure.yt_dlp_client import YTDLPClient

logger = get_logger("MediaQualityFilter")


class MediaQualityFilter:
    """
    Filtro de Qualidade de Mídia Automático para Mapeamento de Canal.
    """

    def __init__(self, min_height: int = 720, min_fps: float = 20.0):
        self.min_height = min_height
        self.min_fps = min_fps
        self.yt_client = YTDLPClient()
        logger.info(f"🛡️ Filtro de Qualidade de Mídia Inicializado (Resolução mín: {min_height}p, FPS mín: {min_fps}).")

    def analyze_video(self, video_url_or_id: str) -> Dict[str, Any]:
        """
        Analisa os metadados brutos de um vídeo do YouTube sem fazer download.
        """
        if not video_url_or_id.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_url_or_id}"
        else:
            video_url = video_url_or_id

        logger.info(f"🔍 Analisando qualidade técnica: {video_url}")
        meta = self.yt_client.get_video_metadata(video_url)

        if not meta or "error" in meta:
            return {
                "video_id": meta.get("id", video_url_or_id) if meta else video_url_or_id,
                "titulo": "Desconhecido",
                "status": "DESQUALIFICADO",
                "motivo": f"Falha ao obter metadados do YouTube: {meta.get('error') if meta else 'Erro'}",
                "resolucao_maxima": 0,
                "fps": 0,
                "duracao_segundos": 0,
                "largura": 0,
                "altura": 0,
                "url": video_url
            }

        # Busca a resolução MÁXIMA disponível entre todos os formatos do YouTube
        formats = meta.get("formats", [])
        all_heights = [f.get("height") for f in formats if f.get("height") is not None]
        height = max(all_heights) if all_heights else (meta.get("height") or 0)

        width = meta.get("width") or 0
        fps = meta.get("fps") or 0.0
        duration = meta.get("duration") or 0
        title = meta.get("title") or "Sem Título"
        video_id = meta.get("id") or video_url_or_id

        # Regra de Qualificação
        motivos = []
        is_approved = True

        if height < self.min_height:
            is_approved = False
            motivos.append(f"Resolução baixa ({height}p < {self.min_height}p)")

        if fps > 0 and fps < self.min_fps:
            is_approved = False
            motivos.append(f"Taxa de quadros baixa ({fps:.1f} fps < {self.min_fps} fps)")

        status = "APROVADO" if is_approved else "DESQUALIFICADO"
        motivo_final = "Qualidade HD Aprovada" if is_approved else "; ".join(motivos)

        result = {
            "video_id": video_id,
            "titulo": title,
            "status": status,
            "motivo": motivo_final,
            "resolucao_maxima": f"{height}p",
            "altura": height,
            "largura": width,
            "fps": fps,
            "duracao_segundos": duration,
            "url": video_url
        }

        if is_approved:
            logger.info(f"✅ Vídeo APROVADO: '{title[:40]}' ({height}p, {fps}fps)")
        else:
            logger.warning(f"⚠️ Vídeo DESQUALIFICADO: '{title[:40]}' ({motivo_final})")

        return result

    def scan_channel_quality(
        self,
        video_items: List[Dict[str, Any]],
        output_dir: Path
    ) -> Tuple[List[Dict[str, Any]], Path, Path]:
        """
        Executa a análise de qualidade em lote para uma lista de vídeos mapeados do canal,
        salvando os relatórios em `data/fase1_mapeamento/`.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        csv_file = output_dir / "relatorio_qualidade_midias.csv"
        json_file = output_dir / "relatorio_qualidade_midias.json"

        results = []
        logger.info(f"📊 Iniciando auditoria técnica de qualidade em {len(video_items)} vídeos...")

        for idx, item in enumerate(video_items, 1):
            v_id = item.get("id") or item.get("video_id") or item.get("url")
            print(f"   [{idx}/{len(video_items)}] Avaliando vídeo ID: {v_id}...")
            res = self.analyze_video(v_id)
            results.append(res)

        # Salva em JSON
        with open(json_file, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

        # Salva em CSV
        fieldnames = [
            "video_id", "titulo", "status", "motivo",
            "resolucao_maxima", "altura", "largura", "fps", "duracao_segundos", "url"
        ]
        with open(csv_file, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow(r)

        aprovados = [r for r in results if r["status"] == "APROVADO"]
        rejeitados = [r for r in results if r["status"] == "DESQUALIFICADO"]

        logger.info(f"✨ Auditoria Concluída: {len(aprovados)} Vídeos Aprovados | {len(rejeitados)} Vídeos Desqualificados.")
        logger.info(f"📄 Relatório salvo em '{csv_file}'")

        return results, csv_file, json_file
