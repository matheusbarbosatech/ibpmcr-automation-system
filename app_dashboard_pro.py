"""
Dashboard Web Pro (Streamlit Frontend) - IBPM CR AUTOMATION SYSTEM.

Foco Principal: Processamento e Mineração dos +400 Áudios Locais via Gemini 1.5 Flash (File API).
Segundário: Ingestão de novos links na barra lateral (Sidebar).

Execução no Terminal:
    streamlit run app_dashboard_pro.py
"""

import os
import json
import requests
import streamlit as st
from pathlib import Path

# Configuração da Página no Streamlit
st.set_page_config(
    page_title="IBPM CR - Acervo & Studio Pro",
    page_icon="🎙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# Estilo CSS Personalizado
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
    .main-header {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF8F00 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #A0AAB0;
        margin-bottom: 1.5rem;
    }
    .stButton>button {
        background: linear-gradient(90deg, #FF4B4B 0%, #D32F2F 100%);
        color: white;
        border-radius: 6px;
        border: none;
        font-weight: 600;
        padding: 0.6rem 1.2rem;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# BARRA LATERAL (SIDEBAR): STATUS DA API + INGESTÃO DE LINKS SECUNDÁRIA
# =============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/youtube-play.png", width=64)
    st.title("IBPM CR Automation")
    st.caption("Ecossistema de Mineração & Edição 9:16")
    st.divider()

    st.markdown("### 📡 Status da API Backend")
    api_online = False
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=3)
        if r.status_code == 200:
            st.success("🟢 API Server Online (Porta 8000)")
            api_online = True
        else:
            st.warning("🟡 Resposta anômala da API")
    except Exception:
        st.error("🔴 API Backend Offline! Inicie no Terminal:")
        st.code("uvicorn src.api.main_api:app --port 8000", language="powershell")

    st.divider()

    # INGESTÃO SECUNDÁRIA POR LINK NA SIDEBAR
    st.markdown("### 📥 Baixar Novo Culto por Link")
    yt_url = st.text_input("URL do YouTube:", placeholder="https://www.youtube.com/watch?v=...", key="sb_url")
    btn_download_sb = st.button("🚀 Baixar Áudio no Padrão", use_container_width=True)

    if btn_download_sb:
        if not yt_url:
            st.warning("⚠️ Insira uma URL válida!")
        else:
            with st.spinner("Downloading MP3..."):
                try:
                    resp = requests.post(f"{API_BASE_URL}/api/v1/ingest", json={"youtube_url": yt_url}, timeout=120)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.success(f"✅ {data.get('file_name')} baixado!")
                        st.rerun()
                    else:
                        st.error(f"Erro: {resp.text}")
                except Exception as e:
                    st.error(f"Falha na API: {e}")


# =============================================================================
# CABEÇALHO PRINCIPAL
# =============================================================================
st.markdown('<div class="main-header">🎙️ ACERVO DE CULTOS & STUDIO PRO</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Mineração Teológica dos +400 Áudios Locais via Gemini 1.5 Flash (Rota Nativa sem Colab)</div>', unsafe_allow_html=True)


# Carrega arquivos de áudios locais no computador
audio_dir = Path("data/audio_podcasts")
insights_dir = Path("data/audio_podcasts/conteudos_fase3")
audio_dir.mkdir(parents=True, exist_ok=True)
insights_dir.mkdir(parents=True, exist_ok=True)

local_mp3_files = sorted([
    f for f in audio_dir.glob("*")
    if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
])

mined_count = len(list(insights_dir.glob("*.insights.json")))
total_audios = len(local_mp3_files)
pending_count = max(0, total_audios - mined_count)

# Métricas no Topo
m1, m2, m3, m4 = st.columns(4)
m1.metric("📂 Áudios Baixados no PC", total_audios)
m2.metric("🟢 Cultos Minerados (Fase 3)", mined_count)
m3.metric("🟡 Pendentes de Mineração", pending_count)
m4.metric("🧠 Modelo de IA", "Gemini 1.5 Flash")

st.divider()


# Abas Principais Focadas no Acervo Local
tab_acervo, tab_editor = st.tabs([
    "🎧 1. Acervo Local & Mineração Gemini 1.5",
    "✂️ 2. Editor de Cortes Virais (FFmpeg 9:16)"
])


# =============================================================================
# ABA 1: ACERVO LOCAL & MINERAÇÃO TEOLÓGICA (FOCO PRINCIPAL)
# =============================================================================
with tab_acervo:
    st.subheader("🎧 Áudios Locais Baixados no seu Computador")
    st.write("Selecione qualquer um dos áudios do seu acervo para rodar a transcrição + mineração teológica na nuvem do Gemini.")

    if not local_mp3_files:
        st.info("Nenhum áudio encontrado na pasta local 'data/audio_podcasts'. Use a barra lateral para baixar um culto.")
    else:
        # Monta opções com indicador visual de status
        options_dict = {}
        for f in local_mp3_files:
            ins_file = insights_dir / f"{f.stem}.insights.json"
            is_mined = ins_file.exists() and ins_file.stat().st_size > 100
            status_icon = "🟢 [MINERADO]" if is_mined else "🟡 [PENDENTE]"
            display_name = f"{status_icon} {f.name} ({round(f.stat().st_size / (1024*1024), 1)} MB)"
            options_dict[display_name] = (f, is_mined)

        col_sel, col_act = st.columns([3, 1])
        with col_sel:
            selected_display = st.selectbox("Escolha um Culto do Acervo:", list(options_dict.keys()))
            selected_file, already_mined = options_dict[selected_display]

        with col_act:
            st.write("")
            st.write("")
            btn_process = st.button("🧠 Processar com Gemini 1.5", use_container_width=True)

        if btn_process:
            v_id = selected_file.stem.split("_")[2] if len(selected_file.stem.split("_")) > 2 else selected_file.stem
            
            with st.spinner(f"📤 Enviando {selected_file.name} para a Gemini File API e analisando teologia na nuvem..."):
                try:
                    resp_min = requests.post(
                        f"{API_BASE_URL}/api/v1/process-gemini",
                        json={"audio_file_path": selected_file.name, "video_id": v_id},
                        timeout=180
                    )
                    if resp_min.status_code == 200:
                        st.balloons()
                        st.success("🎉 Mineração e Transcrição concluídas com sucesso via Gemini 1.5 Flash File API!")
                        st.rerun()
                    else:
                        st.error(f"Erro na API Backend: {resp_min.text}")
                except Exception as e:
                    st.error(f"Falha ao comunicar com a API Backend: {e}")

        st.divider()

        # Exibição do Payload Minerado se o culto selecionado já tiver insights
        ins_path_selected = insights_dir / f"{selected_file.stem}.insights.json"
        if ins_path_selected.exists() and ins_path_selected.stat().st_size > 100:
            st.subheader(f"📊 Relatório de Insights Minerados: {selected_file.stem}")
            with open(ins_path_selected, "r", encoding="utf-8") as f:
                payload_data = json.load(f)

            short_cuts = payload_data.get("short_form_cuts", [])
            mid_cuts = payload_data.get("mid_form_cuts", [])

            c1, c2 = st.columns(2)
            c1.markdown(f"**Cortes Verticais (Short-Form 9:16):** `{len(short_cuts)}`")
            c2.markdown(f"**Cortes Horizontais (Mid-Form 16:9):** `{len(mid_cuts)}`")

            for idx, cut in enumerate(short_cuts, 1):
                with st.expander(f"📌 Corte Short #{idx} - {cut.get('title_hook_a')}"):
                    st.markdown(f"**Título A (Curiosidade):** {cut.get('title_hook_a')}")
                    st.markdown(f"**Título B (Dor/Empatia):** {cut.get('title_hook_b')}")
                    st.markdown(f"**Categoria Homilética:** `{cut.get('category')}`")
                    st.markdown(f"**Emoção Predominante:** `{cut.get('dominant_emotion')}`")
                    st.markdown(f"**Âncora de Início (7 palavras):** `{cut.get('start_anchor_7_words')}`")
                    st.markdown(f"**Âncora de Fim (7 palavras):** `{cut.get('end_anchor_7_words')}`")


# =============================================================================
# ABA 2: EDITOR DE CORTES VIRAIS (FFMPEG 9:16)
# =============================================================================
with tab_editor:
    st.subheader("✂️ Renderização e Edição de Vídeos Verticais (FFmpeg 9:16)")
    st.write("Selecione um culto minerado para renderizar o vídeo vertical com crop 9:16, legendas .ASS Karaokê e normalização EBU R128.")

    mined_files = list(insights_dir.glob("*.insights.json"))

    if not mined_files:
        st.info("Nenhum relatório de mineração encontrado. Processe um culto na Aba 1.")
    else:
        sel_insight_name = st.selectbox("Selecione o Relatório Minerado:", [f.name for f in mined_files])
        
        if sel_insight_name:
            insight_file_path = insights_dir / sel_insight_name
            with open(insight_file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)

            short_cuts = payload.get("short_form_cuts", [])
            video_id_src = payload.get("source_video_id", "FlqCTPRsIT4")

            for idx, cut in enumerate(short_cuts, 1):
                st.markdown(f"### 🎬 Corte Vertical #{idx}: {cut.get('title_hook_a')}")
                
                col_det, col_rnd = st.columns([2, 1])
                with col_det:
                    st.write(f"**Título A:** {cut.get('title_hook_a')}")
                    st.write(f"**Título B:** {cut.get('title_hook_b')}")
                    st.write(f"**Âncora Início:** `{cut.get('start_anchor_7_words')}`")
                    st.write(f"**Âncora Fim:** `{cut.get('end_anchor_7_words')}`")

                with col_rnd:
                    cut_id_str = cut.get("cut_id") or f"short_{idx:03d}"
                    btn_r = st.button(f"🎞️ Renderizar Corte #{idx}", key=f"rnd_{idx}")
                    
                    if btn_r:
                        with st.spinner(f"Renderizando {cut_id_str} no FFmpeg..."):
                            try:
                                r_res = requests.post(
                                    f"{API_BASE_URL}/api/v1/render",
                                    json={
                                        "cut_id": cut_id_str,
                                        "video_url": f"https://www.youtube.com/watch?v={video_id_src}",
                                        "cut_payload": cut,
                                        "start_sec": 0.0,
                                        "end_sec": 45.0
                                    },
                                    timeout=300
                                )
                                if r_res.status_code == 200:
                                    st.success("✅ Renderização concluída!")
                                    clip_path = r_res.json().get("final_video_path")
                                    if clip_path and os.path.exists(clip_path):
                                        st.video(clip_path)
                                else:
                                    st.error(f"Erro na renderização: {r_res.text}")
                            except Exception as e:
                                st.error(f"Falha na API: {e}")

                st.divider()
