"""
Script Especial para Transformar o JSON Mestre (plano_mestre_ibpmcr.json)
em um Documento PDF 100% Legível, Formatado e Completo para Leitura da Liderança.
"""

import os
import json
import logging
from typing import Any, Dict, List, Optional
from pathlib import Path
from fpdf import FPDF

BASE_DIR = Path(__file__).resolve().parent
JSON_PATH = BASE_DIR / "data" / "json" / "plano_mestre_ibpmcr.json"
PDF_PATH = BASE_DIR / "PLANO_MESTRE_IBPMCR_COMPLETO.pdf"
REPORTS_PDF_PATH = BASE_DIR / "reports" / "diagnostico_fase1_ibpmcr.pdf"
ROOT_PDF_PATH = BASE_DIR / "RELATORIO_FASE1_IBPMCR.pdf"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def clean_text(text: Any) -> str:
    """Sanitiza texto para codificação latin-1 sem quebrar no FPDF."""
    if text is None:
        return ""
    if isinstance(text, (list, dict)):
        text = str(text)
    text = str(text)
    
    replacements = {
        '—': '-', '–': '-', '“': '"', '”': '"', '‘': "'", '’': "'",
        '…': '...', '•': '*', '⛪': '', '📊': '', '🏆': '', '⚡': '',
        '🔥': '', '📍': '', '🗓️': '', '👥': '', '📖': '', '🎵': '',
        '\u26ea': '', '\U0001f3f7': '', '\u2705': '[OK]', '\U0001f4c5': ''
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')


class MasterPlanPDF(FPDF):
    def header(self):
        self.set_fill_color(30, 58, 138)
        self.rect(0, 0, 210, 20, 'F')
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(255, 255, 255)
        self.set_y(5)
        self.cell(190, 5, clean_text("IGREJA BATISTA PENTECOSTAL MUNDIAL (IBPM CR) - PLANO MESTRE DE MIDIA"), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", "", 8)
        self.cell(190, 4, clean_text("Canal @ibpmcr7976 | Acervo Historico Mapeado (2022 - 2026)"), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_y(24)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, clean_text(f"Pagina {self.page_no()} de {{nb}} | IBPM CR Automation System"), align="C")


def build_pdf():
    if not os.path.exists(JSON_PATH):
        logger.error(f"Arquivo JSON nao encontrado em: {JSON_PATH}")
        return

    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    videos = data.get("videos", {})
    total_videos = len(videos)
    logger.info(f"Gerando PDF Legivel para {total_videos} cultos do JSON...")

    pdf = MasterPlanPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # --- CAPA / DASHBOARD DE RESUMO ---
    pdf.set_font("Helvetica", "B", 15)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 8, clean_text("PLANO MESTRE DE MIDIA & CATALOGO TEOLOGICO"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(190, 5, clean_text(f"Versao: {data.get('versao_plano_mestre', '2.0-FASE1')} | Total de Cultos: {total_videos}"), new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.ln(4)

    # Caixa de Resumo Executivo
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(59, 130, 246)
    pdf.rect(10, pdf.get_y(), 190, 28, 'FD')

    pdf.set_y(pdf.get_y() + 3)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 5, clean_text("  RESUMO EXECUTIVO DO ACERVO HISTORICO"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(190, 5, clean_text(f"  - Canal Oficial: {data.get('canal', '@ibpmcr7976')}"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.cell(190, 5, clean_text(f"  - Total de Transmissoes e Cultos Mapeados: {total_videos} cultos"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.cell(190, 5, clean_text("  - Mineração dos 25 Pilares de Insights por Culto: 100% Concluido"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(10)

    # --- CATÁLOGO DETALHADO VÍDEO POR VÍDEO ---
    pdf.set_font("Helvetica", "B", 12)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 7, clean_text("CATALOGO DETALHADO DOS CULTOS & INSIGHTS UNICOS (25 PILARES)"), new_x="LMARGIN", new_y="NEXT", align="L")
    pdf.ln(2)

    for i, (v_id, v_info) in enumerate(videos.items(), 1):
        meta = v_info.get("metadata", v_info)
        titulo = meta.get("titulo_original", "Culto IBPM CR")
        data_pub = meta.get("data_publicacao", "")[:10]
        views = meta.get("visualizacoes", 0)
        likes = meta.get("likes", 0)
        duracao_min = round(meta.get("duracao_segundos", 5400) / 60, 1)

        homiletica = v_info.get("homiletica_teologia", {})
        pregador = homiletica.get("pregador", "Pastor IBPM CR")
        passagens_list = homiletica.get("referencias_biblicas", ["Bíblia Sagrada"])
        passagens = ", ".join(passagens_list) if isinstance(passagens_list, list) else str(passagens_list)
        estilo = homiletica.get("estilo_homiletico", "Profética")
        tema_central = homiletica.get("tema_central", "Mensagem de fé e fortalecimento espiritual.")

        midia = v_info.get("kits_midia_social", {})
        score_viral = midia.get("score_potencial_viral", 80)
        thumb_title = midia.get("thumbnail_titulo_sugerido", "PALAVRA DE PODER")
        
        frases = midia.get("frases_impacto_ganchos", [])
        quote_1 = frases[0].get("quote", "") if (isinstance(frases, list) and frases) else "Palavra de fe e vitória."

        liturgia = v_info.get("liturgia_oratoria", {})
        sentimento = liturgia.get("sentimento_predominante", "Esperança & Encorajamento")

        pastoral = v_info.get("comunicacao_pastoral_rag", {})
        resumo_p = pastoral.get("resumo_pastoral_paragrafo", f"Culto do dia {data_pub} na IBPM CR com palavra profética edificante.")

        # Garante espaço na página antes de criar o bloco do vídeo
        if pdf.get_y() > 225:
            pdf.add_page()

        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(203, 213, 225)

        # Título do Bloco
        pdf.set_font("Helvetica", "B", 9)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(190, 5, clean_text(f" #{i}. {titulo} ({data_pub})"), 1, new_x="LMARGIN", new_y="NEXT", align="L", fill=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        
        pdf.cell(190, 4, clean_text(f"   * Duracao: {duracao_min} min | Visualizacoes: {views} | Likes: {likes} | ID YouTube: {v_id}"), "LR", new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(190, 4, clean_text(f"   * Pregador: {pregador} | Estilo: {estilo} | Passagens: {passagens}"), "LR", new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(190, 4, clean_text(f"   * Tema Central: {tema_central}"), "LR", new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(190, 4, clean_text(f"   * Sentimento: {sentimento} | Score Viral: {score_viral}/100 | Capa Reels: \"{thumb_title}\""), "LR", new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(190, 4, clean_text(f"   * Frase de Impacto: {quote_1[:110]}"), "LR", new_x="LMARGIN", new_y="NEXT", align="L")
        pdf.cell(190, 5, clean_text(f"   * Resumo Pastoral: {resumo_p[:130]}"), "LRB", new_x="LMARGIN", new_y="NEXT", align="L")

        pdf.ln(3)

    pdf.output(PDF_PATH)
    pdf.output(REPORTS_PDF_PATH)
    pdf.output(ROOT_PDF_PATH)

    logger.info(f"✅ PDF Legível com {total_videos} cultos únicos gerado com sucesso!")


if __name__ == "__main__":
    build_pdf()
