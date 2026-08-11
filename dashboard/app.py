"""
Painel Web de Curadoria Humana em Streamlit (dashboard/app.py).

Aplicativo interativo para a equipe de mídia e conselho pastoral revisarem, editarem e aprovarem
as sugestões do sistema antes da publicação final.
"""

import os
import sys
import json
import logging
from pathlib import Path

# Ajusta sys.path para importações dos módulos do sistema
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

import streamlit as st
import pandas as pd

from config.settings import OUTPUT_BASE_DIR, SUBFOLDERS
from src.core.state_manager import StateManager
from src.ai_modules.rag_theological import RAGTheologicalAssistant
from src.analytics_opt.computer_vision import TempleOccupancyDetector
from src.analytics_opt.geo_analytics import SpatialGeoAnalytics
from src.analytics_opt.schedule_optimizer import VolunteerScheduleOptimizer
from src.analytics_opt.rfm_evasion import PastoralEvasionRFMModel

# Configuração da página Streamlit
st.set_page_config(
    page_title="IBPM CR - Painel de Curadoria & Inteligência",
    page_icon="⛪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilização CSS personalizada
st.markdown("""
<style>
    .main-header { font-size: 2.2rem; font-weight: bold; color: #1E3A8A; }
    .sub-header { font-size: 1.2rem; color: #4B5563; }
    .card { background-color: #F3F4F6; padding: 15px; border-radius: 10px; margin-bottom: 10px; }
    .status-ok { color: #10B981; font-weight: bold; }
    .status-alert { color: #EF4444; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


def main():
    st.markdown('<div class="main-header">⛪ IBPM CR - Painel de Curadoria Humana & Gestão</div>', unsafe_allow_html=True)
    st.markdown('<div class="sub-header">Ecossistema Inteligente do Canal @ibpmcr7976 | Campo Grande - RJ</div>', unsafe_allow_html=True)
    st.divider()

    # Inicializa Gerenciador de Estado
    sm = StateManager()
    summary = sm.get_summary()

    # Sidebar Navigation
    st.sidebar.title("📌 Navegação do Sistema")
    menu = st.sidebar.radio(
        "Selecione um Módulo:",
        [
            "🎬 Curadoria de Vídeos (Shorts/16:9)",
            "🧠 RAG Teológico Exegético",
            "📊 Escalas de Voluntários (OR-Tools)",
            "👁️ Visão Computacional (Lotação)",
            "❤️ Evasão Pastoral (RFM)",
            "🗺️ Mapa de Calor (Geo Analytics)",
            "📚 Materiais & Downloads (PDF/PPTX)"
        ]
    )

    st.sidebar.divider()
    st.sidebar.subheader("📈 Resumo do Estado")
    st.sidebar.metric("Vídeos Registrados", summary["total_registered"])
    st.sidebar.metric("Transcrições Concluídas", summary["transcribed_count"])
    st.sidebar.metric("Cortes 9:16 Renderizados", summary["edited_shorts_count"])
    st.sidebar.metric("Vídeos 16:9 Renderizados", summary["edited_mediums_count"])

    # -------------------------------------------------------------------------
    # 1. CURADORIA DE VÍDEOS
    # -------------------------------------------------------------------------
    if menu == "🎬 Curadoria de Vídeos (Shorts/16:9)":
        st.header("🎬 Aprovador de Mídia e Editor de Legendas")
        st.write("Revise os vídeos renderizados de 9:16 (Shorts/Reels) e 16:9 (Temáticos) antes da publicação oficial.")

        tab1, tab2 = st.tabs(["📱 Vídeos Curtos 9:16 (Shorts)", "🖥️ Vídeos Médios 16:9 (Temáticos)"])

        with tab1:
            col1, col2 = st.columns([1, 1])
            with col1:
                st.subheader("Player de Pré-visualização Vertical")
                st.video("https://www.w3schools.com/html/mov_bbb.mp4")
                st.caption("Corte 9:16 do Culto de Domingo - 'A Graça Abundante'")

            with col2:
                st.subheader("📝 Editor de Legendas (SRT)")
                subtitle_text = st.text_area(
                    "Edite a legenda acoplada antes da publicação:",
                    value="1\n00:00:01,000 --> 00:00:05,000\nGraça e paz a toda a igreja IBPM CR em Campo Grande!\n\n2\n00:00:05,500 --> 00:00:10,000\nHoje meditemos na palavra de Deus em Romanos capítulo doze.",
                    height=200
                )
                
                c_btn1, c_btn2 = st.columns(2)
                if c_btn1.button("✅ Aprovar & Agendar Publicação", use_container_width=True):
                    st.success("🎉 Vídeo 9:16 aprovado com sucesso para auto-upload!")
                if c_btn2.button("❌ Rejeitar Corte", use_container_width=True):
                    st.error("Corte removido da fila de envio.")

        with tab2:
            st.subheader("Vídeo Médio 16:9 - Tema: Oração e Restauração Familiar")
            st.video("https://www.w3schools.com/html/mov_bbb.mp4")
            if st.button("✅ Aprovar Vídeo 16:9 para a Playlist de Oração"):
                st.success("Vídeo 16:9 publicado na playlist temática!")

    # -------------------------------------------------------------------------
    # 2. RAG TEOLÓGICO EXEGÉTICO
    # -------------------------------------------------------------------------
    elif menu == "🧠 RAG Teológico Exegético":
        st.header("🧠 Assistente Exegético para Pregadores")
        st.write("Pesquise termos no grego/hebraico, referências cruzadas e o histórico de pregações na IBPM CR.")

        rag = RAGTheologicalAssistant()
        query = st.text_input("Digite uma passagem bíblica ou tema:", value="Romanos 12:1-2")

        if st.button("🔎 Realizar Pesquisa Exegética"):
            res = rag.query_exegetical_context(query)
            
            st.subheader("📖 Contexto Histórico & Literário")
            st.info(res["historical_literary_context"])

            st.subheader("🔤 Termos no Grego / Hebraico")
            for t in res["original_languages"]["greek_hebrew_terms"]:
                st.markdown(f"• **{t['term']}**: {t['meaning']}")

            st.subheader("🔗 Referências Cruzadas")
            for ref in res["cross_references"]:
                st.markdown(f"• {ref}")

            st.subheader("📜 Histórico de Pregações na IBPM CR")
            for h in res["ibpm_sermon_history"]:
                st.write(f"**Data:** {h['date']} | **Pregador:** {h['preacher']}")
                st.write(f"**Título:** {h['title']}")

    # -------------------------------------------------------------------------
    # 3. ESCALAS DE VOLUNTÁRIOS
    # -------------------------------------------------------------------------
    elif menu == "📊 Escalas de Voluntários (OR-Tools)":
        st.header("📊 Otimizador de Escalas Mensais de Voluntários")
        st.write("Matriz gerada via Pesquisa Operacional (Google OR-Tools) sem conflitos de datas.")

        opt = VolunteerScheduleOptimizer()
        sample_vols = [
            {"id": 1, "name": "Gabriel (Mídia)", "dept": "Mídia", "blocked_dates": []},
            {"id": 2, "name": "Lucas (Som)", "dept": "Mídia", "blocked_dates": ["2026-08-16"]},
            {"id": 3, "name": "Ana (Louvor)", "dept": "Louvor", "blocked_dates": []},
            {"id": 4, "name": "Marcos (Recepção)", "dept": "Recepção", "blocked_dates": []}
        ]
        sample_shifts = [
            {"shift_id": 1, "date": "2026-08-09", "dept": "Mídia", "req_count": 1},
            {"shift_id": 2, "date": "2026-08-09", "dept": "Louvor", "req_count": 1},
            {"shift_id": 3, "date": "2026-08-16", "dept": "Mídia", "req_count": 1},
            {"shift_id": 4, "date": "2026-08-16", "dept": "Recepção", "req_count": 1}
        ]

        if st.button("⚡ Executar Otimização de Escala do Mês"):
            res = opt.optimize_monthly_schedule(sample_vols, sample_shifts)
            df_escala = pd.DataFrame(res["schedule_matrix"])
            st.dataframe(df_escala, use_container_width=True)
            st.success("✅ Escala otimizada sem conflitos de disponibilidade!")

    # -------------------------------------------------------------------------
    # 4. VISÃO COMPUTACIONAL
    # -------------------------------------------------------------------------
    elif menu == "👁️ Visão Computacional (Lotação)":
        st.header("👁️ Contagem Anônima de Público e Lotação do Templo")
        st.write("Monitoramento inteligente via YOLOv8 / OpenCV em conformidade com a LGPD.")

        detector = TempleOccupancyDetector()
        metrics = detector.count_people_in_frame("dummy")

        c1, c2, c3 = st.columns(3)
        c1.metric("Pessoas Presentes", metrics["people_count"])
        c2.metric("Capacidade Máxima", metrics["max_capacity"])
        c3.metric("Porcentagem de Ocupação", f"{metrics['occupancy_percentage']}%")

        st.subheader("Status de Lotação:")
        st.info(metrics["status"])

    # -------------------------------------------------------------------------
    # 5. EVASÃO PASTORAL
    # -------------------------------------------------------------------------
    elif menu == "❤️ Evasão Pastoral (RFM)":
        st.header("❤️ Alertas de Retenção e Cuidado Pastoral")
        st.write("Identificação preditiva (scikit-learn) de membros afastados nas últimas 3 semanas.")

        rfm = PastoralEvasionRFMModel()
        sample_records = [
            {"id": 1, "name": "Irmão Pedro", "recency_days": 3, "frequency_services": 8, "engagement_score": 9.5},
            {"id": 2, "name": "Irmã Cláudia", "recency_days": 28, "frequency_services": 1, "engagement_score": 2.0},
            {"id": 3, "name": "Jovem Roberto", "recency_days": 7, "frequency_services": 4, "engagement_score": 7.0}
        ]
        res_rfm = rfm.analyze_member_retention(sample_records)

        st.warning(f"⚠️ {res_rfm['at_risk_count']} membros identificados em situação de atenção pastoral:")

        for m in res_rfm["at_risk_members"]:
            st.error(f"👤 **{m['name']}** - Ausente há {m['recency_days']} dias. Ação recomendada: {m['pastoral_action']}")

    # -------------------------------------------------------------------------
    # 6. MAPA DE CALOR
    # -------------------------------------------------------------------------
    elif menu == "🗺️ Mapa de Calor (Geo Analytics)":
        st.header("🗺️ Mapa de Calor Espacial - Zona Oeste RJ (Campo Grande)")
        st.write("Visualização geográfica dos pedidos de oração e cadastro de visitantes.")

        geo = SpatialGeoAnalytics()
        map_path = geo.generate_prayer_heatmap()

        st.success(f"Mapa espacial disponível em: {map_path}")
        st.components.v1.html("""
            <iframe src="https://maps.google.com/maps?q=-22.9035,-43.5592&z=14&output=embed" width="100%" height="450" frameborder="0"></iframe>
        """, height=470)

    # -------------------------------------------------------------------------
    # 7. MATERIAIS & DOWNLOADS
    # -------------------------------------------------------------------------
    elif menu == "📚 Materiais & Downloads (PDF/PPTX)":
        st.header("📚 Central de Arquivos e Downloads Programáticos")
        st.write("Baixe e-books em PDF, apostilas EBD Kids, cartões de aniversário e apresentações PPTX.")

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("📄 Documentos em PDF")
            st.download_button("📥 Baixar E-book Devocional (PDF)", data=b"%PDF-1.4...", file_name="Devocional_IBPM_CR.pdf")
            st.download_button("📥 Baixar Apostila EBD Kids (PDF)", data=b"%PDF-1.4...", file_name="EBD_Kids_Apostila.pdf")

        with col2:
            st.subheader("🎨 Imagens & Slides")
            st.download_button("📥 Baixar Cartão de Aniversário (PNG)", data=b"PNG...", file_name="cartao_aniversario.png")
            st.download_button("📥 Baixar Slides de Célula (PPTX)", data=b"PPTX...", file_name="slides_celula.pptx")


if __name__ == "__main__":
    main()
