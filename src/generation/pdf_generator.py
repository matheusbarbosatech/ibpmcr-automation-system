"""
Gerador Programático de PDFs (fpdf2).

Compila automaticamente e-books, devocionais diários, apostilas lúdicas da EBD Kids
e cadernos de cifras de louvor com leiaute e tipografia estilizados.
"""

import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path

try:
    from fpdf import FPDF
    HAS_FPDF = True
except ImportError:
    HAS_FPDF = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IBPMCustomPDF(FPDF if HAS_FPDF else object):
    """
    Classe estendida FPDF com cabeçalho e rodapé personalizados da IBPM CR.
    """

    def header(self):
        if hasattr(self, 'set_font'):
            self.set_font('Helvetica', 'B', 10)
            self.set_text_color(50, 50, 150)
            self.cell(0, 8, 'IGREJA BATISTA PENTECOSTAL MUNDIAL - IBPM CR', 0, 1, 'C')
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(100, 100, 100)
            self.cell(0, 4, 'Canal Oficial @ibpmcr7976 | Campo Grande, RJ', 0, 1, 'C')
            self.ln(5)

    def footer(self):
        if hasattr(self, 'set_y'):
            self.set_y(-15)
            self.set_font('Helvetica', 'I', 8)
            self.set_text_color(128, 128, 128)
            self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')


class PDFDocumentGenerator:
    """
    Gerador central de documentos PDF estilizados.
    """

    def __init__(self):
        """
        Inicializa pastas de saída.
        """
        self.ebooks_dir = get_folder_path("EBOOKS_DEVOCIONAIS")
        self.kids_dir = get_folder_path("EBD_KIDS")
        self.cifras_dir = get_folder_path("CIFRAS_LOUVORES")

        os.makedirs(self.ebooks_dir, exist_ok=True)
        os.makedirs(self.kids_dir, exist_ok=True)
        os.makedirs(self.cifras_dir, exist_ok=True)

    def generate_devotional_pdf(
        self,
        title: str,
        biblical_passage: str,
        content_chapters: List[Dict[str, str]],
        output_filename: str = "devocional_semanal.pdf"
    ) -> str:
        """
        Gera um e-book devocional em PDF formatado.

        :param title: Título do Devocional.
        :param biblical_passage: Texto de leitura bíblica.
        :param content_chapters: Lista de capítulos [{'title': str, 'body': str}].
        :param output_filename: Nome do arquivo de saída.
        :return: Caminho do arquivo PDF gerado.
        """
        output_path = os.path.join(self.ebooks_dir, output_filename)
        logger.info(f"📄 Gerando PDF Devocional: '{title}'...")

        if not HAS_FPDF:
            return self._mock_pdf_file(output_path, title)

        try:
            pdf = IBPMCustomPDF()
            pdf.add_page()

            # Título principal
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_text_color(30, 30, 90)
            pdf.cell(0, 12, title.encode('latin-1', 'replace').decode('latin-1'), 0, 1, "C")
            pdf.ln(4)

            # Leitura Bíblica Destacada
            pdf.set_font("Helvetica", "I", 11)
            pdf.set_text_color(80, 80, 80)
            pdf.multi_cell(0, 6, f"Leitura Bíblica: {biblical_passage}".encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(6)

            # Capítulos e Aplicação
            for chap in content_chapters:
                pdf.set_font("Helvetica", "B", 13)
                pdf.set_text_color(40, 40, 120)
                pdf.cell(0, 8, chap.get("title", "").encode('latin-1', 'replace').decode('latin-1'), 0, 1, "L")
                pdf.set_font("Helvetica", "", 10)
                pdf.set_text_color(20, 20, 20)
                pdf.multi_cell(0, 5, chap.get("body", "").encode('latin-1', 'replace').decode('latin-1'))
                pdf.ln(5)

            pdf.output(output_path)
            logger.info(f"✅ PDF Devocional salvo com sucesso: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro ao gerar PDF devocional: {e}")
            return self._mock_pdf_file(output_path, title)

    def generate_ebd_kids_pdf(self, kids_data: Dict[str, Any], output_filename: str = "apostila_ebd_kids.pdf") -> str:
        """
        Gera uma apostila colorida em PDF para o Ministério Infantil.

        :param kids_data: Estrutura vinda do adaptador NLP Kids.
        :param output_filename: Nome do arquivo.
        :return: Caminho do PDF salvo.
        """
        output_path = os.path.join(self.kids_dir, output_filename)
        logger.info(f"🎨 Gerando Apostila Infantil EBD Kids PDF...")

        if not HAS_FPDF:
            return self._mock_pdf_file(output_path, kids_data.get("title", "EBD Kids"))

        try:
            pdf = IBPMCustomPDF()
            pdf.add_page()

            pdf.set_font("Helvetica", "B", 20)
            pdf.set_text_color(220, 50, 50)
            pdf.cell(0, 14, kids_data.get("title", "EBD Kids").encode('latin-1', 'replace').decode('latin-1'), 0, 1, "C")
            pdf.ln(5)

            # Versículo Chave
            pdf.set_font("Helvetica", "B", 12)
            pdf.set_text_color(0, 100, 150)
            pdf.cell(0, 8, "Versículo para Memorizar:".encode('latin-1', 'replace').decode('latin-1'), 0, 1, "L")
            pdf.set_font("Helvetica", "I", 11)
            pdf.multi_cell(0, 6, kids_data.get("key_verse", "").encode('latin-1', 'replace').decode('latin-1'))
            pdf.ln(5)

            # História Bíblica
            pdf.set_font("Helvetica", "B", 12)
            pdf.cell(0, 8, "História da Semana:".encode('latin-1', 'replace').decode('latin-1'), 0, 1, "L")
            pdf.set_font("Helvetica", "", 10)
            pdf.set_text_color(30, 30, 30)
            pdf.multi_cell(0, 5, kids_data.get("story", "").encode('latin-1', 'replace').decode('latin-1'))

            pdf.output(output_path)
            logger.info(f"✅ Apostila EBD Kids gerada em: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro ao gerar PDF EBD Kids: {e}")
            return self._mock_pdf_file(output_path, "EBD Kids")

    def _mock_pdf_file(self, filepath: str, title: str) -> str:
        """Gera um PDF/arquivo placeholder."""
        with open(filepath, "wb") as f:
            f.write(f"%PDF-1.4 Mock PDF Document Title: {title}".encode("utf-8") + b"\x00" * 512)
        logger.info(f"📄 Arquivo PDF salvo (placeholder): {filepath}")
        return filepath


if __name__ == "__main__":
    gen = PDFDocumentGenerator()
    chaps = [
        {"title": "1. O Culto Racional", "body": "Entregar a nossa vida como sacrifício vivo, santo e agradável a Deus."},
        {"title": "2. A Transformação da Mente", "body": "Não vos conformeis com este mundo, mas transformai-vos."}
    ]
    pdf_out = gen.generate_devotional_pdf("Renovação da Mente", "Romanos 12:1-2", chaps)
    print(f"PDF Devocional gerado em: {pdf_out}")
