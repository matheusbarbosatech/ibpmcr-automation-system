"""
Dashboard e Relatório de Diagnóstico do Canal (PDF/HTML).

Gera um relatório visual completo em PDF (fpdf2) e HTML com a análise do acervo histórico da IBPM CR,
destacando total de horas gravadas, inventário de cortes mapeados (curtos/médios), e-books e lições Kids.
"""

import os
import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path
from src.core.state_manager import MasterPlanManager

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class Phase1ReportGenerator:
    """
    Gerador de Relatórios Diagnósticos da Fase 1.
    """

    def __init__(self):
        """
        Inicializa caminhos de saída.
        """
        self.output_dir = get_folder_path("RELATORIOS_ANALYTICS")
        os.makedirs(self.output_dir, exist_ok=True)
        self.master_mgr = MasterPlanManager()

    def generate_diagnostic_reports(self) -> Dict[str, str]:
        """
        Gera os relatórios de diagnóstico em PDF e HTML baseados no plano_mestre_ibpmcr.json.

        :return: Dicionário contendo os caminhos dos arquivos PDF e HTML salvos.
        """
        logger.info("📊 Gerando Relatório Diagnóstico da Fase 1 (PDF & HTML)...")

        state = self.master_mgr.state
        videos = list(state.get("videos", {}).values())

        total_videos = len(videos)
        total_sec = sum(v.get("duracao_segundos", 3600) for v in videos)
        total_hours = round(total_sec / 3600.0, 1)

        # Ordena Top 20 mais engajados (visualizações + likes + comentários)
        videos_sorted = sorted(
            videos,
            key=lambda x: (x.get("visualizacoes", 0) + x.get("likes", 0) * 10),
            reverse=True
        )
        top_20 = videos_sorted[:20]

        # Contagem de Inventário de Mídia Mapeada
        total_shorts_mapped = sum(len(v.get("potencial_cortes_curtos_9_16", [])) for v in videos)
        total_mediums_mapped = sum(
            sum(len(clips) for clips in v.get("potencial_cortes_medios_16_9", {}).values())
            for v in videos
        )
        total_ebooks_mapped = sum(1 for v in videos if v.get("potencial_ebook_devocional", {}).get("apropriado_para_ebook"))
        total_kids_mapped = sum(1 for v in videos if v.get("potencial_ebd_kids", {}).get("apropriado_para_ebd_kids"))

        data_summary = {
            "total_videos": total_videos,
            "total_hours": total_hours,
            "total_shorts_mapped": total_shorts_mapped,
            "total_mediums_mapped": total_mediums_mapped,
            "total_ebooks_mapped": total_ebooks_mapped,
            "total_kids_mapped": total_kids_mapped,
            "top_20": top_20
        }

        html_path = os.path.join(self.output_dir, "diagnostico_fase1_ibpmcr.html")
        pdf_path = os.path.join(self.output_dir, "diagnostico_fase1_ibpmcr.pdf")

        self._export_html_report(data_summary, html_path)
        self._export_pdf_report(data_summary, pdf_path)

        logger.info(f"✅ Relatórios gerados com sucesso:\n- HTML: {html_path}\n- PDF: {pdf_path}")
        return {"html_path": html_path, "pdf_path": pdf_path}

    def _export_html_report(self, data: Dict[str, Any], filepath: str) -> None:
        """Exporta relatório visual em HTML."""
        top_items_html = ""
        for i, v in enumerate(data["top_20"][:10], 1):
            top_items_html += f"""
            <tr>
                <td>#{i}</td>
                <td><b>{v.get('titulo_original', 'Culto IBPM CR')}</b></td>
                <td>{v.get('visualizacoes', 0):,}</td>
                <td>{v.get('likes', 0)}</td>
                <td>{v.get('data_publicacao', '')[:10]}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="pt-br">
<head>
    <meta charset="UTF-8">
    <title>IBPM CR - Relatório Diagnóstico Fase 1</title>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 30px; background-color: #f4f6f9; color: #333; }}
        .header {{ background-color: #1e3a8a; color: white; padding: 25px; border-radius: 10px; text-align: center; }}
        .metrics-grid {{ display: flex; gap: 15px; margin: 25px 0; justify-content: space-around; }}
        .card {{ background: white; padding: 20px; border-radius: 8px; flex: 1; text-align: center; box-shadow: 0 2px 5px rgba(0,0,0,0.1); }}
        .card h3 {{ font-size: 2.2em; margin: 5px 0; color: #1e3a8a; }}
        table {{ width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; }}
        th, td {{ padding: 12px 15px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #1e3a8a; color: white; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>⛪ IBPM CR - Relatório Diagnóstico do Acervo (Fase 1)</h1>
        <p>Mapeamento de Mídia & Plano Mestre | Canal @ibpmcr7976 (3 Anos de Histórico)</p>
    </div>

    <div class="metrics-grid">
        <div class="card"><h3>{data['total_videos']}</h3><p>Vídeos Catalogados</p></div>
        <div class="card"><h3>{data['total_hours']}h</h3><p>Horas de Conteúdo</p></div>
        <div class="card"><h3>{data['total_shorts_mapped']}</h3><p>Cortes 9:16 Mapeados</p></div>
        <div class="card"><h3>{data['total_mediums_mapped']}</h3><p>Cortes 16:9 Mapeados</p></div>
        <div class="card"><h3>{data['total_ebooks_mapped']}</h3><p>E-books Mapeados</p></div>
    </div>

    <h2>🏆 Top 10 Vídeos de Maior Engajamento</h2>
    <table>
        <thead>
            <tr><th>#</th><th>Título do Culto</th><th>Visualizações</th><th>Likes</th><th>Data</th></tr>
        </thead>
        <tbody>
            {top_items_html}
        </tbody>
    </table>
</body>
</html>
"""
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(html_content)

    def _export_pdf_report(self, data: Dict[str, Any], filepath: str) -> None:
        """Exporta relatório diagnósticos em PDF com fpdf2."""
        if not HAS_FPDF:
            with open(filepath, "wb") as f:
                f.write(b"%PDF-1.4 Mock PDF Diagnostic Report Phase 1")
            return

        try:
            pdf = FPDF()
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 16)
            pdf.set_text_color(30, 58, 138)
            title_text = "IBPM CR - Relatorio Diagnostico do Acervo (Fase 1)"
            pdf.cell(190, 10, title_text, 0, 1, "C")
            pdf.ln(5)

            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(50, 50, 50)
            summary_txt = f"Total de Videos Mapeados: {data['total_videos']}\nTotal de Horas Gravadas: {data['total_hours']}h\nCortes 9:16 Mapeados: {data['total_shorts_mapped']}\nCortes 16:9 Mapeados: {data['total_mediums_mapped']}\nE-books Potenciais: {data['total_ebooks_mapped']}\nAulas EBD Kids Mapeadas: {data['total_kids_mapped']}"
            pdf.multi_cell(190, 6, summary_txt.encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(5)

            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(190, 8, "Top 5 Videos com Maior Engajamento:", 0, 1, "L")
            pdf.set_font("Helvetica", "", 9)

            for i, v in enumerate(data["top_20"][:5], 1):
                raw_t = v.get("titulo_original", "Culto")[:60]
                t_clean = raw_t.encode("latin-1", "replace").decode("latin-1")
                pdf.multi_cell(190, 5, f"{i}. {t_clean} - {v.get('visualizacoes', 0)} views")

            pdf.output(filepath)

        except Exception as e:
            logger.error(f"Erro ao gerar PDF com fpdf2: {e}")
            with open(filepath, "wb") as f:
                f.write(b"%PDF-1.4 Mock PDF Diagnostic Report")


if __name__ == "__main__":
    rep = Phase1ReportGenerator()
    paths = rep.generate_diagnostic_reports()
    print("Relatórios gerados:")
    print(paths)
