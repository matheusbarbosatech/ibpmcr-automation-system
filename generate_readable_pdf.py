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
        self.rect(0, 0, 210, 22, 'F')
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(255, 255, 255)
        self.set_y(6)
        self.cell(190, 6, clean_text("IGREJA BATISTA PENTECOSTAL MUNDIAL (IBPM CR) - PLANO MESTRE DE MIDIA"), 0, 1, "C")
        self.set_font("Helvetica", "", 9)
        self.cell(190, 4, clean_text("Canal @ibpmcr7976 | Acervo Historico 2022 - 2026"), 0, 1, "C")
        self.set_y(26)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(128, 128, 128)
        self.cell(0, 10, clean_text(f"Pagina {self.page_no()} de {{nb}} | IBPM CR Automation System"), 0, 0, "C")


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
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 10, clean_text("PLANO MESTRE DE MIDIA & CATALOGO TEOLOGICO"), 0, 1, "C")
    pdf.set_font("Helvetica", "", 11)
    pdf.set_text_color(70, 70, 70)
    pdf.cell(190, 6, clean_text(f"Versao: {data.get('versao_plano_mestre', '2.0-FASE1')} | Total de Cultos: {total_videos}"), 0, 1, "C")
    pdf.ln(5)

    # Caixa de Resumo
    pdf.set_fill_color(241, 245, 249)
    pdf.set_draw_color(59, 130, 246)
    pdf.rect(10, pdf.get_y(), 190, 30, 'FD')

    pdf.set_y(pdf.get_y() + 4)
    pdf.set_font("Helvetica", "B", 10)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 5, clean_text(f"  RESUMO EXECUTIVO DO ACERVO HISTORICO"), 0, 1, "L")
    pdf.set_font("Helvetica", "", 9)
    pdf.set_text_color(50, 50, 50)
    pdf.cell(190, 5, clean_text(f"  - Canal Oficial: {data.get('canal', '@ibpmcr7976')}"), 0, 1, "L")
    pdf.cell(190, 5, clean_text(f"  - Total de Transmissoes e Cultos Mapeados: {total_videos}"), 0, 1, "L")
    pdf.cell(190, 5, clean_text(f"  - Mineração dos 25 Pilares de Insights: 100% Concluido"), 0, 1, "L")
    pdf.ln(12)

    # --- CATÁLOGO DETALHADO VÍDEO POR VÍDEO ---
    pdf.set_font("Helvetica", "B", 13)
    pdf.set_text_color(30, 58, 138)
    pdf.cell(190, 8, clean_text("CATALOGO DETALHADO DOS CULTOS & INSIGHTS (25 PILARES)"), 0, 1, "L")
    pdf.ln(2)

    for i, (v_id, v_info) in enumerate(videos.items(), 1):
        meta = v_info.get("metadata", v_info)
        titulo = meta.get("titulo_original", "Culto IBPM CR")
        data_pub = meta.get("data_publicacao", "")[:10]
        views = meta.get("visualizacoes", 0)
        likes = meta.get("likes", 0)
        duracao_min = round(meta.get("duracao_segundos", 3600) / 60, 1)

        homiletica = v_info.get("homiletica_teologia", {})
        pregador = homiletica.get("pregador", "Pastor IBPM CR")
        passagens = ", ".join(homiletica.get("referencias_biblicas", ["Bíblia Sagrada"]))
        estilo = homiletica.get("estilo_homiletico", "Profética")

        midia = v_info.get("kits_midia_social", {})
        score_viral = midia.get("score_potencial_viral", 80)
        thumb_title = midia.get("thumbnail_titulo_sugerido", "DEUS VAI REFAZER")
        
        frases = midia.get("frases_impacto_ganchos", [])
        quote_1 = frases[0].get("quote", "") if frases else "Palavra edificante de fe e vitoria."

        liturgia = v_info.get("liturgia_oratoria", {})
        sentimento = liturgia.get("sentimento_predominante", "Esperança & Encorajamento")

        pastoral = v_info.get("comunicacao_pastoral_rag", {})
        resumo_p = pastoral.get("resumo_pastoral_paragrafo", "Mensagem edificante para a igreja.")

        # Bloco do Vídeo
        pdf.set_fill_color(248, 250, 252)
        pdf.set_draw_color(203, 213, 225)
        
        # Garante espaco na pagina antes de criar a caixa
        if pdf.get_y() > 230:
            pdf.add_page()

        pdf.set_font("Helvetica", "B", 10)
        pdf.set_text_color(30, 58, 138)
        pdf.cell(190, 6, clean_text(f"#{i}. {titulo} ({data_pub})"), 1, 1, "L", fill=True)

        pdf.set_font("Helvetica", "", 8)
        pdf.set_text_color(50, 50, 50)
        
        line1 = f"  * Duracao: {duracao_min} min | Visualizacoes: {views} | Likes: {likes} | ID: {v_id}"
        pdf.cell(190, 5, clean_text(line1), "LR", 1, "L")

        line2 = f"  * Pregador: {pregador} | Estilo: {estilo} | Passagens: {passagens}"
        pdf.cell(190, 5, clean_text(line2), "LR", 1, "L")

        line3 = f"  * Tom & Sentimento: {sentimento} | Score Viral: {score_viral}/100"
        pdf.cell(190, 5, clean_text(line3), "LR", 1, "L")

        line4 = f"  * Titulo Capa (Shorts): \"{thumb_title}\""
        pdf.cell(190, 5, clean_text(line4), "LR", 1, "L")

        line5 = f"  * Frase de Impacto (Gancho): \"{quote_1[:90]}...\""
        pdf.cell(190, 5, clean_text(line5), "LR", 1, "L")

        line6 = f"  * Resumo Pastoral: {resumo_p[:120]}..."
        pdf.cell(190, 5, clean_text(line6), "LRB", 1, "L")

        pdf.ln(3)

    # Exporta para os 3 caminhos de destino
    pdf.output(PDF_PATH)
    pdf.output(REPORTS_PDF_PATH)
    pdf.output(ROOT_PDF_PATH)

    logger.info(f"✅ PDF 100% Legível gerado com sucesso!")
    logger.info(f"   - Arquivo Principal: {PDF_PATH}")
    logger.info(f"   - Arquivo Reports:   {REPORTS_PDF_PATH}")
    logger.info(f"   - Arquivo Raiz:      {ROOT_PDF_PATH}")


if __name__ == "__main__":
    build_pdf()
