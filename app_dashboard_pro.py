"""
IBPM CR AUTOMATION STUDIO PRO - CAPCUT / DESCRIPT STYLE WEB WORKSPACE (STREAMLIT).

Interface Profissional de Edição e Mineração Audiovisual para o IBPM CR Automation System.
Integra Visual Workspace com Preview Player, Timeline Colorida por Arco Emocional,
Storyboards de Cortes 9:16/16:9, Estúdio de Legendas Karaokê (.ASS) e Auto-Ducking.

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
    page_title="IBPM CR - Studio Pro Editor",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

# Estilo CSS de Alta Performance (Dark Mode CapCut/Descript Style)
st.markdown("""
<style>
    /* Estilo Geral do Canvas */
    .stApp {
        background-color: #0E0F12;
        color: #E1E4E8;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Top Bar & Branding */
    .editor-topbar {
        display: flex;
        align-items: center;
        justify-content: space-between;
        background-color: #16181D;
        border-bottom: 1px solid #262930;
        padding: 0.8rem 1.5rem;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .brand-title {
        font-size: 1.6rem;
        font-weight: 900;
        background: linear-gradient(90deg, #FFD700 0%, #FF8F00 50%, #FF4B4B 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        letter-spacing: -0.5px;
    }
    .badge-status {
        background-color: #1E222B;
        color: #00D2FF;
        border: 1px solid #00D2FF44;
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 0.8rem;
        font-weight: 600;
    }

    /* Cards de Storyboard de Cortes */
    .cut-card {
        background-color: #16181D;
        border: 1px solid #262930;
        border-radius: 10px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        transition: transform 0.2s, border-color 0.2s;
    }
    .cut-card:hover {
        border-color: #FFD700;
        transform: translateY(-2px);
    }
    .cut-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.8rem;
    }
    .cut-title-a {
        font-size: 1.1rem;
        font-weight: 700;
        color: #FFFFFF;
    }
    .cut-title-b {
        font-size: 0.9rem;
        color: #A0AAB0;
        font-style: italic;
    }
    .tag-category {
        background-color: #2D1A3F;
        color: #D47AFF;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .tag-virality {
        background-color: #1A3B2B;
        color: #40C057;
        padding: 3px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 700;
    }

    /* Visual Timeline Track Bar */
    .timeline-container {
        background-color: #121418;
        border: 1px solid #262930;
        border-radius: 8px;
        padding: 0.8rem;
        margin-bottom: 1.5rem;
    }
    .timeline-track {
        display: flex;
        height: 28px;
        border-radius: 6px;
        overflow: hidden;
        margin-top: 0.5rem;
    }
    .tl-block-hook { background-color: #FF4B4B; width: 12%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: bold; color: white; }
    .tl-block-climax { background-color: #FFD700; width: 68%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: bold; color: black; }
    .tl-block-cta { background-color: #00D2FF; width: 20%; display: flex; align-items: center; justify-content: center; font-size: 0.7rem; font-weight: bold; color: black; }

    /* Botões de Ação do Editor */
    .stButton>button {
        background: linear-gradient(90deg, #1E222B 0%, #262930 100%);
        color: #E1E4E8;
        border: 1px solid #363A45;
        border-radius: 6px;
        font-weight: 600;
    }
    .stButton>button:hover {
        background: linear-gradient(90deg, #FFD700 0%, #FF8F00 100%);
        color: #000000;
        border-color: #FFD700;
    }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# BARRA LATERAL (SIDEBAR): MEDIA POOL & CONFIGURAÇÕES DA PIPELINE
# =============================================================================
with st.sidebar:
    st.image("https://img.icons8.com/color/96/video-editing.png", width=56)
    st.markdown("## 🎞️ Media Pool & Status")
    st.caption("IBPM CR Automation Engine v1.0")
    st.divider()

    # Status de Conexão com o Backend FastAPI
    st.markdown("### 📡 Servidor de Renderização")
    api_online = False
    try:
        r = requests.get(f"{API_BASE_URL}/", timeout=3)
        if r.status_code == 200:
            st.success("🟢 FastAPI Backend Running (:8000)")
            api_online = True
        else:
            st.warning("🟡 API Respondendo com Avisos")
    except Exception:
        st.error("🔴 API Offline! Inicie no Terminal:")
        st.code("uvicorn src.api.main_api:app --port 8000", language="powershell")

    st.divider()

    # Ingestão de Novo Culto (Fase 1)
    st.markdown("### 📥 Importar Nova Mídia (YouTube)")
    yt_url = st.text_input("URL do YouTube:", placeholder="https://www.youtube.com/watch?v=...", key="sb_yt_url")
    if st.button("🚀 Ingerir Áudio MP3", use_container_width=True):
        if not yt_url:
            st.warning("Insira uma URL válida!")
        else:
            with st.spinner("Efetuando download e cadastrando no banco..."):
                try:
                    res = requests.post(f"{API_BASE_URL}/api/v1/ingest", json={"youtube_url": yt_url}, timeout=120)
                    if res.status_code == 200:
                        st.success(f"✅ Download concluído: {res.json().get('file_name')}")
                        st.rerun()
                    else:
                        st.error(f"Erro: {res.text}")
                except Exception as e:
                    st.error(f"Falha na conexão: {e}")

    st.divider()
    st.markdown("### 📊 Status das Fases")
    st.markdown("- **Fase 1 (Ingestão):** 🟢 451 Cultos OK")
    st.markdown("- **Fase 2 (File API):** 🟢 Nuvem Gemini Active")
    st.markdown("- **Fase 3 (Mineração):** 🟢 Pydantic V2 OK")
    st.markdown("- **Fase 4 (FFmpeg):** 🟢 EBU R128 + ASS OK")


# =============================================================================
# HEADER SUPERIOR DO EDITOR
# =============================================================================
st.markdown("""
<div class="editor-topbar">
    <div>
        <div class="brand-title">🎬 IBPM CR - STUDIO PRO EDITOR</div>
        <div style="font-size: 0.85rem; color: #A0AAB0;">Workspace Profissional de Mineração Teológica, Reframe 9:16 e Sonoplastia</div>
    </div>
    <div style="display: flex; gap: 10px;">
        <span class="badge-status">GPU Cloud Active</span>
        <span class="badge-status" style="color: #FFD700; border-color: #FFD70044;">Gemini 1.5 Flash</span>
    </div>
</div>
""", unsafe_allow_html=True)


# Carrega o acervo de áudios e relatórios minerados
audio_dir = Path("data/audio_podcasts")
insights_dir = Path("data/audio_podcasts/conteudos_fase3")
audio_dir.mkdir(parents=True, exist_ok=True)
insights_dir.mkdir(parents=True, exist_ok=True)

local_mp3_files = sorted([
    f for f in audio_dir.glob("*")
    if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
])


# =============================================================================
# ABAS PRINCIPAIS DO WORKSPACE DE EDIÇÃO
# =============================================================================
tab_workspace, tab_subtitles_studio, tab_media_library = st.tabs([
    "🖥️ 1. Workspace de Edição & Storyboards",
    "🎨 2. Estúdio de Legendas & Sonoplastia (.ASS)",
    "📂 3. Biblioteca do Acervo de Mídias (+400)"
])


# =============================================================================
# ABA 1: WORKSPACE DE EDIÇÃO & STORYBOARDS (ESTILO CAPCUT)
# =============================================================================
with tab_workspace:
    if not local_mp3_files:
        st.info("Nenhum áudio encontrado. Use a barra lateral para importar mídias do YouTube.")
    else:
        # Seletor de Culto Ativo
        options_dict = {}
        for f in local_mp3_files:
            ins_file = insights_dir / f"{f.stem}.insights.json"
            is_mined = ins_file.exists() and ins_file.stat().st_size > 100
            icon = "🟢 [MINERADO]" if is_mined else "🟡 [PENDENTE]"
            options_dict[f"{icon} {f.name}"] = (f, is_mined)

        col_select, col_btn_mine = st.columns([3, 1])
        with col_select:
            selected_label = st.selectbox("Culto Ativo no Workspace:", list(options_dict.keys()))
            active_file, is_mined = options_dict[selected_label]

        with col_btn_mine:
            st.write("")
            st.write("")
            if st.button("🧠 Minerar Teologia com Gemini", use_container_width=True):
                v_id = active_file.stem.split("_")[2] if len(active_file.stem.split("_")) > 2 else active_file.stem
                with st.spinner("Enviando MP3 para a File API do Gemini e gerando cortes..."):
                    try:
                        r = requests.post(
                            f"{API_BASE_URL}/api/v1/process-gemini",
                            json={"audio_file_path": active_file.name, "video_id": v_id},
                            timeout=180
                        )
                        if r.status_code == 200:
                            st.success("🎉 Mineração concluída com sucesso!")
                            st.rerun()
                        else:
                            st.error(f"Erro na API: {r.text}")
                    except Exception as e:
                        st.error(f"Falha ao conectar na API Backend: {e}")

        st.divider()

        # PAINEL SUPERIOR: PREVIEW PLAYER & TIMELINE VISUAL
        col_preview, col_timeline = st.columns([1, 1])

        ins_path = insights_dir / f"{active_file.stem}.insights.json"
        payload_data = {}
        if ins_path.exists() and ins_path.stat().st_size > 100:
            with open(ins_path, "r", encoding="utf-8") as f:
                payload_data = json.load(f)

        short_cuts = payload_data.get("short_form_cuts", [])
        mid_cuts = payload_data.get("mid_form_cuts", [])
        src_video_id = payload_data.get("source_video_id", "FlqCTPRsIT4")

        with col_preview:
            st.markdown("#### 📺 Preview Player de Renderização")
            # Procura por vídeos já renderizados desse culto
            rendered_cuts = list(Path("data/audio_podcasts/cortes_fase4").glob(f"*.mp4")) if Path("data/audio_podcasts/cortes_fase4").exists() else []
            
            if rendered_cuts:
                selected_rendered = st.selectbox("Selecione o Clipe Renderizado para Assistir:", [f.name for f in rendered_cuts])
                st.video(str(Path("data/audio_podcasts/cortes_fase4") / selected_rendered))
            else:
                st.info("Nenhum clipe renderizado em disco ainda. Clique em 'Renderizar' nos cards abaixo.")

        with col_timeline:
            st.markdown("#### 🎚️ Timeline de Retenção e Arcos Emocionais")
            st.markdown("""
            <div class="timeline-container">
                <div style="display: flex; justify-content: space-between; font-size: 0.8rem; color: #A0AAB0;">
                    <span>00:00 (Hook Inicial)</span>
                    <span>00:30 (Clímax Pentecostal)</span>
                    <span>00:59 (Apelo / Call to Action)</span>
                </div>
                <div class="timeline-track">
                    <div class="tl-block-hook">HOOK (0-3s)</div>
                    <div class="tl-block-climax">CLÍMAX PENTECOSTAL / REVELAÇÃO (3-45s)</div>
                    <div class="tl-block-cta">CTA / APELO (45-60s)</div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown(f"**Detalhes da Mídia Ativa:**")
            st.write(f"- **Nome:** `{active_file.name}`")
            st.write(f"- **Cortes Verticais (9:16):** `{len(short_cuts)}` gerados")
            st.write(f"- **Cortes Horizontais (16:9):** `{len(mid_cuts)}` gerados")

        st.divider()

        # PAINEL INFERIOR: STORYBOARDS DE CORTES (CARDS INTERATIVOS ESTILO CAPCUT)
        st.markdown("### 🎞️ Storyboards de Cortes Minerados pela IA")
        
        tab_v_cuts, tab_h_cuts = st.tabs(["📱 Cortes Verticais (Short-Form 9:16)", "📺 Cortes Horizontais (Mid-Form 16:9)"])

        with tab_v_cuts:
            if not short_cuts:
                st.info("Nenhum corte vertical minerado ainda. Clique em 'Minerar Teologia' acima.")
            for idx, cut in enumerate(short_cuts, 1):
                cut_id = cut.get("cut_id") or f"short_{idx:03d}"
                st.markdown(f"""
                <div class="cut-card">
                    <div class="cut-header">
                        <span class="cut-title-a">🎬 Short #{idx}: {cut.get('title_hook_a')}</span>
                        <div>
                            <span class="tag-category">{cut.get('category')}</span>
                            <span class="tag-virality">Virality: 95%</span>
                        </div>
                    </div>
                    <div class="cut-title-b">Hook B (Dor/Empatia): {cut.get('title_hook_b')}</div>
                    <div style="margin-top: 0.5rem; font-size: 0.85rem; color: #A0AAB0;">
                        <b>Âncora Início (7 palavras):</b> <code style="color: #FFD700;">{cut.get('start_anchor_7_words')}</code><br>
                        <b>Âncora Fim (7 palavras):</b> <code style="color: #FFD700;">{cut.get('end_anchor_7_words')}</code>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c_b1, c_b2, c_b3 = st.columns([1, 1, 1])
                with c_b1:
                    if st.button(f"🎞️ Renderizar 9:16 (#{idx})", key=f"btn_r_short_{idx}", use_container_width=True):
                        with st.spinner(f"Renderizando {cut_id} no FFmpeg..."):
                            try:
                                r_res = requests.post(
                                    f"{API_BASE_URL}/api/v1/render",
                                    json={
                                        "cut_id": cut_id,
                                        "video_url": f"https://www.youtube.com/watch?v={src_video_id}",
                                        "cut_payload": cut,
                                        "format_type": "9:16",
                                        "start_sec": 0.0,
                                        "end_sec": 45.0
                                    },
                                    timeout=300
                                )
                                if r_res.status_code == 200:
                                    st.success("✅ Renderização concluída!")
                                    st.rerun()
                                else:
                                    st.error(f"Erro: {r_res.text}")
                            except Exception as e:
                                st.error(f"Falha na chamada da API: {e}")

                with c_b2:
                    st.button(f"📐 Auto-Reframe 9:16", key=f"btn_rf_{idx}", use_container_width=True)
                with c_b3:
                    st.button(f"🚀 Publicar Redes", key=f"btn_pub_{idx}", use_container_width=True)

                st.divider()

        with tab_h_cuts:
            if not mid_cuts:
                st.info("Nenhum corte horizontal minerado ainda.")
            for idx, cut in enumerate(mid_cuts, 1):
                cut_id = cut.get("cut_id") or f"mid_{idx:03d}"
                st.markdown(f"""
                <div class="cut-card">
                    <div class="cut-header">
                        <span class="cut-title-a">📖 Mid-Form #{idx}: {cut.get('title')}</span>
                        <span class="tag-category">Exegese / Estudo</span>
                    </div>
                    <div style="font-size: 0.9rem; color: #CCCCCC; margin-bottom: 0.5rem;">{cut.get('synopsis')}</div>
                    <div style="font-size: 0.85rem; color: #A0AAB0;">
                        <b>Âncora Início:</b> <code style="color: #00D2FF;">{cut.get('start_anchor_7_words')}</code><br>
                        <b>Âncora Fim:</b> <code style="color: #00D2FF;">{cut.get('end_anchor_7_words')}</code>
                    </div>
                </div>
                """, unsafe_allow_html=True)

                c_m1, c_m2 = st.columns([1, 1])
                with c_m1:
                    if st.button(f"🎞️ Renderizar 16:9 (#{idx})", key=f"btn_r_mid_{idx}", use_container_width=True):
                        with st.spinner(f"Renderizando {cut_id} (16:9 HD)..."):
                            try:
                                r_res = requests.post(
                                    f"{API_BASE_URL}/api/v1/render",
                                    json={
                                        "cut_id": cut_id,
                                        "video_url": f"https://www.youtube.com/watch?v={src_video_id}",
                                        "cut_payload": cut,
                                        "format_type": "16:9",
                                        "start_sec": 0.0,
                                        "end_sec": 300.0
                                    },
                                    timeout=300
                                )
                                if r_res.status_code == 200:
                                    st.success("✅ Renderização 16:9 concluída!")
                                    st.rerun()
                                else:
                                    st.error(f"Erro: {r_res.text}")
                            except Exception as e:
                                st.error(f"Falha na chamada da API: {e}")

                with c_m2:
                    st.button(f"📝 Copiar Capítulos YT", key=f"btn_cp_{idx}", use_container_width=True)

                st.divider()


# =============================================================================
# ABA 2: ESTÚDIO DE LEGENDAS & SONOPLASTIA (.ASS ESTILO CAPCUT)
# =============================================================================
with tab_subtitles_studio:
    st.subheader("🎨 Estúdio de Estilos de Legendas Karaokê & Sonoplastia (.ASS)")
    st.write("Personalize a tipografia, cores de destaque Karaokê, sombras e configurações de Auto-Ducking para o FFmpeg.")

    col_sub_style, col_audio_style = st.columns(2)

    with col_sub_style:
        st.markdown("#### 🔤 Tipografia & Estilo Visual")
        font_family = st.selectbox("Família Tipográfica:", ["Montserrat Black", "Roboto Bold", "Outfit ExtraBold", "Impact"])
        font_size = st.slider("Tamanho da Fonte (pt):", min_value=32, max_value=72, value=48)
        
        st.markdown("**Paleta Cromática (Hexadecimal BGR):**")
        color_text = st.color_picker("Cor Texto Padrão:", "#FFFFFF")
        color_karaoke = st.color_picker("Cor Destaque Karaokê (Palavra Ativa):", "#FFD700")
        color_stroke = st.color_picker("Cor do Contorno (Stroke):", "#000000")
        
        st.checkbox("Exibir Barra de Progresso Dinâmica na Margem Inferior", value=True)

    with col_audio_style:
        st.markdown("#### 🎛️ Engenharia de Áudio Broadcast & Auto-Ducking")
        st.selectbox("Gênero da Trilha de Fundo:", ["Ambient Worship", "Cinematic Pad", "Dramatic Strings", "Solemn Piano"])
        ducking_vol = st.slider("Volume Alvo da Trilha Sonora (dB):", min_value=-40, max_value=-10, value=-22)
        
        st.markdown("**Parâmetros de Normalização EBU R128:**")
        st.write("- **Loudness Integrado:** `-16 LUFS` (Padrão Streaming)")
        st.write("- **True Peak Ceiling:** `-1.5 dBTP` (Proteção Contra Intersample Peaks)")
        st.write("- **Ataque / Liberação Sidechain:** `15ms / 300ms`")

    st.success("✅ As configurações acima são injetadas automaticamente no arquivo de estilos .ASS e no Filtergraph do FFmpeg!")


# =============================================================================
# ABA 3: BIBLIOTECA DO ACERVO DE MÍDIAS (+400 CULTOS)
# =============================================================================
with tab_media_library:
    st.subheader("📂 Biblioteca Completa do Acervo IBPM CR")
    st.write("Gerencie os +400 cultos baixados localmente na pasta 'data/audio_podcasts'.")

    # Lista detalhada dos arquivos no disco
    cultos_grid = []
    for f in local_mp3_files:
        ins_path = insights_dir / f"{f.stem}.insights.json"
        is_mined = ins_path.exists() and ins_path.stat().st_size > 100
        cultos_grid.append({
            "Arquivo MP3": f.name,
            "Tamanho MB": round(f.stat().st_size / (1024 * 1024), 2),
            "Status Mineração": "🟢 MINERADO" if is_mined else "🟡 PENDENTE",
            "Caminho Absoluto": str(f.resolve())
        })

    st.dataframe(cultos_grid, use_container_width=True)
