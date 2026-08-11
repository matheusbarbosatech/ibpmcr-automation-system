"""
Módulo de Varredura Completa do Acervo & Análise de Canal.

Varre todo o histórico do canal @ibpmcr7976 do 1º ao mais recente vídeo,
registra os metadados no estado_videos.json e gera um relatório analítico detalhado.
"""

import os
import json
import logging
from typing import Dict, Any, List
from datetime import datetime
from collections import Counter
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

from config.settings import get_folder_path
from src.core.youtube_api import YouTubeAPIClient
from src.core.state_manager import StateManager

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ChannelCatalogAnalyzer:
    """
    Analisador e varredor completo do canal do YouTube IBPM CR (@ibpmcr7976).
    """

    def __init__(self):
        """
        Inicializa clientes e pastas de saída.
        """
        self.yt_client = YouTubeAPIClient()
        self.state_mgr = StateManager()
        self.analytics_dir = get_folder_path("RELATORIOS_ANALYTICS")
        os.makedirs(self.analytics_dir, exist_ok=True)

    def run_full_scan_and_analysis(self, limit: int = 500) -> Dict[str, Any]:
        """
        Executa a varredura completa de todo o histórico do canal, registra no banco de estado
        e compila o relatório analítico antes de iniciar o processamento pesado de vídeos.

        :param limit: Limite de vídeos a varrer.
        :return: Dicionário consolidado de estatísticas.
        """
        logger.info(f"🔍 Iniciando VARREDURA COMPLETA do canal @ibpmcr7976 (do 1º ao vídeo mais recente)...")

        # 1. Recupera acervo histórico via API ou Mock
        all_videos = self.yt_client.fetch_historical_catalog(limit=limit)
        most_viewed = self.yt_client.fetch_most_viewed_videos(max_results=limit)

        # 2. Registra todos os vídeos no estado_videos.json
        for v in all_videos:
            self.state_mgr.register_video(
                video_id=v["video_id"],
                title=v["title"],
                published_at=v["published_at"],
                view_count=v.get("view_count", 0)
            )

        # Atualiza a ordenação das 3 filas
        historical_ids = [v["video_id"] for v in reversed(all_videos)]  # 1º ao 440º vídeo
        most_viewed_ids = [v["video_id"] for v in most_viewed]
        recent_ids = [v["video_id"] for v in all_videos[:10]]

        self.state_mgr.update_queues(
            recent_ids=recent_ids,
            most_viewed_ids=most_viewed_ids,
            historical_ids=historical_ids
        )

        # 3. Compila Métricas e Estatísticas
        total_videos = len(all_videos)
        total_views = sum(v.get("view_count", 0) for v in all_videos)
        avg_views = round(total_views / max(1, total_videos), 1)

        # Análise dos tópicos/palavras-chave nos títulos
        words = []
        for v in all_videos:
            title_words = [w.capitalize() for w in v["title"].split() if len(w) > 3 and w.lower() not in ["culto", "ibpm", "para", "com", "este"]]
            words.extend(title_words)

        frequent_themes = Counter(words).most_common(10)

        report = {
            "channel": "@ibpmcr7976",
            "scan_timestamp": datetime.now().isoformat(),
            "total_videos_cataloged": total_videos,
            "total_views_accumulated": total_views,
            "average_views_per_video": avg_views,
            "top_10_most_viewed": most_viewed[:10],
            "frequent_themes_in_titles": frequent_themes,
            "queues_status": self.state_mgr.get_summary()
        }

        # 4. Salva Relatórios em JSON e Markdown
        json_report_path = os.path.join(self.analytics_dir, "relatorio_varredura_canal.json")
        md_report_path = os.path.join(self.analytics_dir, "relatorio_varredura_canal.md")

        with open(json_report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        self._export_markdown_report(report, md_report_path)

        logger.info(f"✅ Varredura concluída com sucesso! Relatório gerado em: {md_report_path}")
        return report

    def _export_markdown_report(self, report: Dict[str, Any], filepath: str) -> None:
        """Gera o relatório executivo em formato Markdown."""
        md = f"""# 📊 Relatório Executivo de Varredura do Canal @ibpmcr7976

**Data da Varredura:** {report['scan_timestamp']}  
**Canal:** IBPM CR (Campo Grande - RJ)

---

## 📈 Métricas Gerais do Acervo
- **Total de Vídeos Catalogados:** {report['total_videos_cataloged']} vídeos
- **Total de Visualizações Acumuladas:** {report['total_views_accumulated']:,} visualizações
- **Média de Visualizações por Vídeo:** {report['average_views_per_video']} views

---

## 🔥 Temas e Palavras-Chave Mais Frequentes
"""
        for theme, count in report["frequent_themes_in_titles"]:
            md += f"- **{theme}**: {count} ocorrências\n"

        md += "\n---\n\n## 🏆 Top 5 Vídeos Mais Vistos do Canal\n"
        for i, v in enumerate(report["top_10_most_viewed"][:5], 1):
            md += f"{i}. **{v['title']}** - {v.get('view_count', 0):,} visualizações\n"

        md += "\n---\n\n*Relatório gerado automaticamente antes do início do processamento de mídias por IA.*"

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(md)


if __name__ == "__main__":
    analyzer = ChannelCatalogAnalyzer()
    res = analyzer.run_full_scan_and_analysis()
    print("Resumo da Varredura do Canal:")
    print(f"Total de Vídeos: {res['total_videos_cataloged']}")
    print(f"Total de Views: {res['total_views_accumulated']}")
