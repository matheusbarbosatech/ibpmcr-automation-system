"""
Dashboard Web Pro (Streamlit Frontend) - IBPM CR AUTOMATION SYSTEM.

Painel visual interativo estilo CapCut/Submagic para gestão completa do pipeline:
1. Ingestão de cultos via URL do YouTube
2. Mineração teológica e transcrição pela Rota Nativa do Gemini 1.5 Flash
3. Edição, renderização de vídeos verticais (9:16) e pré-visualização.

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
    page_title="IBPM CR - Studio Pro Automation",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")


# Custom CSS para estética visual moderna e responsiva
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
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.0rem;
        color: #A0AAB0;
        margin-bottom: 2rem;
    }
    .metric-card {
        background-color: #161B22;
        border: 1px solid #30363D;
        border-radius: 8px;
        padding: 1.2rem;
        margin-bottom: 1rem;
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
""", unsafe_allow_dict=True)


# Sidebar com Status da Conexão
with st.sidebar:
    st.image("https://img.icons8.com/color/96/youtube-play.png", width=64)
    st.title("IBPM CR Automation")
    st.caption("Sistema Industrial de Mineração & Edição 9:16")
    st.divider()

    st.markdown("### 📡 Conexão Backend API")
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=3)
        if r.status_code == 200:
            st.success("🟢 API Server Online (Porta 8000)")
        else:
            st.warning("🟡 Resposta anômala da API")
    except Exception:
        st.error("🔴 API Backend Offline! Inicie uvicorn no Terminal:")
        st.code("uvicorn src.api.main_api:app --port 8000", language="powershell")

    st.divider()
    st.markdown("### ⚙️ Configurações Rápidas")
    st.info("Modelo de IA: Gemini 1.5 Flash\nResolução Target: 1080x1920 (9:16)\nLoudness Target: -16 LUFS")


# Cabeçalho Principal
st.markdown('<div class="main-header">🎬 IBPM CR AUTOMATION STUDIO PRO</div>', unsafe_allow_dict=True)
st.markdown('<div class="sub-header">Plataforma Autônoma de Mineração Teológica, Reframe 9:16 e Renderização Programática</div>', unsafe_allow_dict=True)


# Abas da Aplicação Web
tab_ingest, tab_mining, tab_editor = st.tabs([
    "📥 1. Ingestão por Link (YouTube)",
    "🧠 2. Mineração Teológica (Gemini 1.5)",
    "✂️ 3. Editor & Cortes Virais (FFmpeg)"
])


# =============================================================================
# ABA 1: INGESTÃO POR LINK
# =============================================================================
with tab_ingest:
    st.subheader("📥 Ingestão Direta de Cultos por Link do YouTube")
    st.write("Cole o link de qualquer transmissão ou vídeo do canal para baixar o MP3 padronizado no sistema.")

    col1, col2 = st.columns([3, 1])
    with col1:
        yt_url = st.text_input("URL do Vídeo no YouTube:", placeholder="https://www.youtube.com/watch?v=FlqCTPRsIT4")
    with col2:
        st.write("")
        st.write("")
        btn_download = st.button("🚀 Baixar Áudio MP3", use_container_width=True)

    if btn_download:
        if not yt_url:
            st.warning("⚠️ Insira uma URL válida do YouTube!")
        else:
            with st.spinner("📥 Efetuando download cirúrgico e registrando no banco SQLite..."):
                try:
                    resp = requests.post(f"{API_BASE_URL}/api/v1/ingest", json={"youtube_url": yt_url}, timeout=120)
                    if resp.status_code == 200:
                        data = resp.json()
                        st.balloons()
                        st.success(f"🎉 {data.get('message')}")
                        
                        col_a, col_b, col_c = st.columns(3)
                        col_a.metric("Nome do Arquivo", data.get("file_name"))
                        col_b.metric("Tamanho MB", f"{data.get('size_mb')} MB")
                        col_c.metric("Status", "🟢 Baixado")
                    else:
                        st.error(f"Erro na API: {resp.text}")
                except Exception as e:
                    st.error(f"Falha na comunicação com o servidor API: {e}")


# =============================================================================
# ABA 2: MINERAÇÃO INTELIGENTE VIA GEMINI
# =============================================================================
with tab_mining:
    st.subheader("🧠 Mineração Teológica Nativa (Gemini 1.5 Flash File API)")
    st.write("Selecione um culto baixado para enviar o MP3 diretamente para os servidores do Google e extrair os cortes virais.")

    # Busca a lista de cultos da API
    audio_files_list = []
    try:
        resp_cultos = requests.get(f"{API_BASE_URL}/api/v1/cultos", timeout=5)
        if resp_cultos.status_code == 200:
            audio_files_list = resp_cultos.json().get("cultos", [])
    except Exception:
        pass

    if not audio_files_list:
        # Fallback lendo arquivos locais na pasta data/audio_podcasts
        audio_dir = Path("data/audio_podcasts")
        if audio_dir.exists():
            for f in audio_dir.glob("*.mp4"):
                audio_files_list.append({"nome_arquivo_mp3": f.name, "titulo_original": f.stem, "video_id": f.stem})

    if not audio_files_list:
        st.info("Nenhum culto encontrado na pasta local. Baixe um culto na Aba 1 primeiro.")
    else:
        options = {f"{c.get('nome_arquivo_mp3', c.get('titulo_original'))}": c for c in audio_files_list}
        selected_key = st.selectbox("Selecione o Culto para Processamento:", list(options.keys()))
        selected_item = options[selected_key]

        btn_process_gemini = st.button("🔥 Minerar com Gemini 1.5 Flash (Rota Nativa File API)")

        if btn_process_gemini:
            fn = selected_item.get("nome_arquivo_mp3") or selected_item.get("titulo_original")
            v_id = selected_item.get("video_id", "IBPM_CULTO")
            
            with st.spinner("🧠 Enviando MP3 para a File API do Gemini e executando a análise teológica..."):
                try:
                    resp_min = requests.post(
                        f"{API_BASE_URL}/api/v1/process-gemini",
                        json={"audio_file_path": fn, "video_id": v_id},
                        timeout=180
                    )
                    if resp_min.status_code == 200:
                        res_data = resp_min.json()
                        st.success("🎉 Mineração Teológica concluída com sucesso!")
                        payload = res_data.get("payload", {})
                        
                        st.subheader("📊 Relatório de Cortes Virais Encontrados")
                        short_cuts = payload.get("short_form_cuts", [])
                        mid_cuts = payload.get("mid_form_cuts", [])
                        
                        col_x, col_y = st.columns(2)
                        col_x.metric("Cortes Curtos (9:16)", len(short_cuts))
                        col_y.metric("Cortes Médios (16:9)", len(mid_cuts))
                        
                        for i, cut in enumerate(short_cuts, 1):
                            with st.expander(f"📌 Corte #{i} - {cut.get('title_hook_a')}"):
                                st.write(f"**Título A (Curiosidade):** {cut.get('title_hook_a')}")
                                st.write(f"**Título B (Dor/Empatia):** {cut.get('title_hook_b')}")
                                st.write(f"**Categoria:** {cut.get('category')} | **Emoção:** {cut.get('dominant_emotion')}")
                                st.write(f"**Âncora Início (7 palavras):** `{cut.get('start_anchor_7_words')}`")
                                st.write(f"**Âncora Fim (7 palavras):** `{cut.get('end_anchor_7_words')}`")
                    else:
                        st.error(f"Erro no processamento: {resp_min.text}")
                except Exception as e:
                    st.error(f"Falha na requisição para o servidor API: {e}")


# =============================================================================
# ABA 3: EDITOR & CORTES VIRAIS
# =============================================================================
with tab_editor:
    st.subheader("✂️ Studio Editor - Renderização de Cortes no FFmpeg (9:16)")
    st.write("Selecione os relatórios minerados para renderizar e visualizar o vídeo final pronto para redes sociais.")

    insights_dir = Path("data/audio_podcasts/conteudos_fase3")
    insights_files = list(insights_dir.glob("*.insights.json")) if insights_dir.exists() else []

    if not insights_files:
        st.info("Nenhum relatório de insights minerado encontrado. Processe um culto na Aba 2.")
    else:
        selected_ins = st.selectbox("Selecione o Relatório Minerado:", [f.name for f in insights_files])
        
        if selected_ins:
            ins_path = insights_dir / selected_ins
            with open(ins_path, "r", encoding="utf-8") as f:
                payload_data = json.load(f)

            short_cuts = payload_data.get("short_form_cuts", [])
            video_id_src = payload_data.get("source_video_id", "FlqCTPRsIT4")

            for idx, cut in enumerate(short_cuts, 1):
                st.markdown(f"### 🎬 Corte #{idx}: {cut.get('title_hook_a')}")
                
                col_info, col_render = st.columns([2, 1])
                with col_info:
                    st.write(f"**Título Hook A:** {cut.get('title_hook_a')}")
                    st.write(f"**Título Hook B:** {cut.get('title_hook_b')}")
                    st.write(f"**Âncora Inicial:** `{cut.get('start_anchor_7_words')}`")
                    st.write(f"**Âncora Final:** `{cut.get('end_anchor_7_words')}`")
                
                with col_render:
                    cut_id_str = cut.get("cut_id") or f"short_{idx:03d}"
                    btn_render = st.button(f"🎞️ Renderizar FFmpeg #{idx}", key=f"btn_r_{idx}")
                    
                    if btn_render:
                        with st.spinner(f"Renderizando clipe {cut_id_str} via FFmpeg (Crop 9:16 + Subtitles .ASS + EBU R128)..."):
                            try:
                                r_resp = requests.post(
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
                                if r_resp.status_code == 200:
                                    st.success(f"✅ Corte #{idx} renderizado com sucesso!")
                                    res_clip = r_resp.json()
                                    clip_path = res_clip.get("final_video_path")
                                    if clip_path and os.path.exists(clip_path):
                                        st.video(clip_path)
                                else:
                                    st.error(f"Erro na renderização: {r_resp.text}")
                            except Exception as e:
                                st.error(f"Falha na chamada de renderização: {e}")

                st.divider()
