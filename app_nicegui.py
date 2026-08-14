"""
IBPM CR AUTOMATION STUDIO PRO - NICEGUI APPLICATION.

Interface Web de Alta Performance estilo CapCut / Descript desenvolvida em NiceGUI + Tailwind CSS.
Suporta Dark Mode imersivo, Studio Workspace de Edição, Ingestão por Link e Mineração Nativa via Gemini File API.

Execução no Terminal:
    python app_nicegui.py
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List

from nicegui import ui, app

# Suporte UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("NiceGUIStudioApp")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

audio_dir = Path("data/audio_podcasts")
insights_dir = Path("data/audio_podcasts/conteudos_fase3")
cuts_dir = Path("data/audio_podcasts/cortes_fase4")

audio_dir.mkdir(parents=True, exist_ok=True)
insights_dir.mkdir(parents=True, exist_ok=True)
cuts_dir.mkdir(parents=True, exist_ok=True)

# Servidor estático para mídias
app.add_static_files("/media", "data")


def get_local_audios() -> List[Path]:
    """Retorna os áudios válidos no disco local."""
    return sorted([
        f for f in audio_dir.glob("*")
        if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
    ])


@ui.page('/')
def main_page():
    ui.dark_mode().enable()

    # Estilo Customizado CapCut/Descript via Tailwind + CSS
    ui.add_head_html("""
    <style>
        body {
            background-color: #0F1117;
            font-family: 'Inter', sans-serif;
            color: #E2E8F0;
        }
        .bg-studio-panel {
            background-color: #1A1D24;
            border: 1px solid #2D313E;
        }
        .text-gold {
            color: #F59E0B;
        }
        .btn-gradient {
            background: linear-gradient(90deg, #F59E0B 0%, #EF4444 100%);
            color: white;
            font-weight: 700;
        }
    </style>
    """)

    # HEADER PROFISSIONAL (Nível da Página)
    with ui.header().classes("bg-[#1A1D24] border-b border-[#2D313E] px-6 py-3 flex justify-between items-center"):
        with ui.row().classes("items-center gap-3"):
            ui.icon("movie", size="2.2rem").classes("text-amber-500")
            ui.label("IBPM CR - STUDIO PRO").classes("text-xl font-extrabold text-amber-500 tracking-tight")
            ui.badge("CapCut / Descript Engine", color="amber-9").classes("text-xs font-bold")

        with ui.row().classes("items-center gap-4"):
            ui.badge("Gemini 1.5 Flash Active", color="blue-9").classes("text-xs")
            ui.badge("FastAPI :8000", color="green-9").classes("text-xs")

    # SIDEBAR DE NAVEGAÇÃO E STATUS (Nível da Página)
    with ui.left_drawer(value=True).classes("bg-[#161820] w-64 border-r border-[#2D313E] p-4 flex flex-col justify-between"):
        with ui.column().classes("w-full gap-4"):
            ui.label("PANEL NAVIGATION").classes("text-xs font-bold text-gray-400 tracking-wider")
            
            with ui.column().classes("w-full gap-2"):
                ui.button("🎬 Studio Workspace", icon="dashboard").classes("w-full text-left justify-start btn-gradient")
                ui.button("📥 Ingestão por Link", icon="download").classes("w-full text-left justify-start bg-[#1A1D24]")
                ui.button("🧠 Mineração Gemini", icon="psychology").classes("w-full text-left justify-start bg-[#1A1D24]")

            ui.separator().classes("bg-[#2D313E] my-2")
            ui.label("PIPELINE STATUS").classes("text-xs font-bold text-gray-400 tracking-wider")
            ui.label("• Fase 1 (Ingestão): OK (451)").classes("text-xs text-gray-300")
            ui.label("• Fase 2 (File API): Active").classes("text-xs text-gray-300")
            ui.label("• Fase 3 (Mineração): Active").classes("text-xs text-gray-300")
            ui.label("• Fase 4 (FFmpeg 9:16): Active").classes("text-xs text-gray-300")

        ui.label("v1.0.0 • IBPM Automation").classes("text-xs text-gray-500 text-center w-full")

    # ÁREA DE CONTEÚDO PRINCIPAL (TABS WORKSPACE)
    with ui.column().classes("w-full p-6 gap-6 bg-[#0F1117]"):
        
        with ui.tabs().classes("w-full bg-[#1A1D24] text-white rounded-lg p-1 border border-[#2D313E]") as tabs:
            tab_workspace = ui.tab("🖥️ Studio Workspace (Editor 9:16 / 16:9)")
            tab_ingest = ui.tab("📥 Ingestão & Links (YouTube)")
            tab_mining = ui.tab("🧠 Mineração Gemini (File API)")

        with ui.tab_panels(tabs, value=tab_workspace).classes("w-full bg-transparent"):
            
            # TAB 1: STUDIO WORKSPACE
            with ui.tab_panel(tab_workspace).classes("w-full p-0 gap-6"):
                audios = get_local_audios()
                
                if not audios:
                    ui.label("Nenhum áudio encontrado. Importe uma mídia na aba de Ingestão.").classes("text-yellow-500 font-bold")
                else:
                    audio_options = {f.name: f for f in audios}
                    
                    with ui.card().classes("w-full bg-studio-panel p-4 rounded-xl flex flex-row items-center justify-between"):
                        with ui.row().classes("items-center gap-4 w-2/3"):
                            ui.label("Culto Ativo:").classes("font-bold text-amber-500")
                            select_audio = ui.select(list(audio_options.keys()), value=list(audio_options.keys())[0]).classes("w-full")

                        def trigger_gemini_mine():
                            selected_f = audio_options[select_audio.value]
                            v_id = selected_f.stem.split("_")[2] if len(selected_f.stem.split("_")) > 2 else selected_f.stem
                            ui.notify(f"📤 Enviando {selected_f.name} para a Gemini File API...", type="info")
                            
                            try:
                                res = requests.post(
                                    f"{API_BASE_URL}/api/v1/process-gemini",
                                    json={"audio_file_path": selected_f.name, "video_id": v_id},
                                    timeout=180
                                )
                                if res.status_code == 200:
                                    ui.notify("🎉 Mineração concluída com sucesso!", type="positive")
                                else:
                                    ui.notify(f"Erro na API: {res.text}", type="negative")
                            except Exception as e:
                                ui.notify(f"Falha na requisição: {e}", type="negative")

                        ui.button("🧠 Minerar com Gemini", on_click=trigger_gemini_mine).classes("btn-gradient px-6")

                    with ui.row().classes("w-full gap-6 no-wrap"):
                        with ui.card().classes("w-1/2 bg-studio-panel p-4 rounded-xl gap-3"):
                            ui.label("📺 Preview Player de Renderização").classes("font-bold text-lg text-white")
                            rendered_clips = list(cuts_dir.glob("*.mp4"))
                            if rendered_clips:
                                clip_select = ui.select([c.name for c in rendered_clips], value=rendered_clips[0].name).classes("w-full")
                                ui.video(f"/media/audio_podcasts/cortes_fase4/{clip_select.value}").classes("w-full rounded-lg")
                            else:
                                ui.label("Nenhum vídeo renderizado em disco. Clique em Renderizar nos storyboards abaixo.").classes("text-gray-400 text-sm")

                        with ui.card().classes("w-1/2 bg-studio-panel p-4 rounded-xl gap-3"):
                            ui.label("🎚️ Timeline de Retenção Visual & Arcos").classes("font-bold text-lg text-white")
                            
                            with ui.column().classes("w-full gap-2 p-3 bg-[#0F1117] rounded-lg border border-[#2D313E]"):
                                with ui.row().classes("w-full justify-between text-xs text-gray-400"):
                                    ui.label("00:00 (Hook Inicial)")
                                    ui.label("00:30 (Clímax Pentecostal)")
                                    ui.label("00:59 (Apelo Final)")

                                with ui.row().classes("w-full h-8 rounded-md overflow-hidden gap-0"):
                                    ui.label("HOOK (0-3s)").classes("w-2/12 bg-red-600 flex items-center justify-center text-xs font-bold text-white")
                                    ui.label("CLÍMAX PENTECOSTAL / EXEGESE (3-45s)").classes("w-8/12 bg-amber-500 flex items-center justify-center text-xs font-bold text-black")
                                    ui.label("CTA (45-60s)").classes("w-2/12 bg-cyan-500 flex items-center justify-center text-xs font-bold text-black")

                            ui.label("Engenharia de Áudio: EBU R128 (-16 LUFS) • Auto-Ducking (-22dB) • ASS Subtitles Karaokê").classes("text-xs text-gray-400 mt-2")

                    ui.label("🎞️ Storyboards de Cortes Minerados").classes("font-bold text-xl text-white mt-4")

                    def render_storyboards():
                        selected_f = audio_options[select_audio.value]
                        ins_f = insights_dir / f"{selected_f.stem}.insights.json"
                        
                        if not ins_f.exists() or ins_f.stat().st_size < 100:
                            ui.label("Nenhum relatório de cortes minerado para este culto ainda. Clique em 'Minerar com Gemini' acima.").classes("text-gray-400")
                            return

                        with open(ins_f, "r", encoding="utf-8") as f_json:
                            payload = json.load(f_json)

                        short_cuts = payload.get("short_form_cuts", [])
                        src_id = payload.get("source_video_id", "FlqCTPRsIT4")

                        with ui.row().classes("w-full gap-4 flex-wrap"):
                            for idx, cut in enumerate(short_cuts, 1):
                                c_id = cut.get("cut_id") or f"short_{idx:03d}"
                                
                                with ui.card().classes("w-full md:w-[48%] bg-studio-panel p-4 rounded-xl border border-[#2D313E] gap-2 hover:border-amber-500 transition-all"):
                                    with ui.row().classes("w-full justify-between items-center"):
                                        ui.label(f"🎬 Short #{idx}: {cut.get('title_hook_a')}").classes("font-bold text-base text-white")
                                        ui.badge(cut.get("category", "Hook"), color="purple-9").classes("text-xs font-bold")

                                    ui.label(f"Hook B: {cut.get('title_hook_b')}").classes("text-xs text-gray-400 italic")
                                    
                                    with ui.column().classes("w-full text-xs text-gray-300 bg-[#0F1117] p-2 rounded border border-[#2D313E] my-2"):
                                        ui.label(f"Âncora Início: {cut.get('start_anchor_7_words')}").classes("text-amber-400 font-mono")
                                        ui.label(f"Âncora Fim: {cut.get('end_anchor_7_words')}").classes("text-amber-400 font-mono")

                                    def make_render_handler(cid=c_id, c_data=cut, vid=src_id):
                                        def handler():
                                            ui.notify(f"🎞️ Renderizando clipe {cid} no FFmpeg...", type="info")
                                            try:
                                                r_res = requests.post(
                                                    f"{API_BASE_URL}/api/v1/render",
                                                    json={
                                                        "cut_id": cid,
                                                        "video_url": f"https://www.youtube.com/watch?v={vid}",
                                                        "cut_payload": c_data,
                                                        "format_type": "9:16",
                                                        "start_sec": 0.0,
                                                        "end_sec": 45.0
                                                    },
                                                    timeout=300
                                                )
                                                if r_res.status_code == 200:
                                                    ui.notify("✅ Renderização 9:16 concluída!", type="positive")
                                                else:
                                                    ui.notify(f"Erro: {r_res.text}", type="negative")
                                            except Exception as err:
                                                ui.notify(f"Falha na API: {err}", type="negative")
                                        return handler

                                    with ui.row().classes("w-full gap-2 mt-2"):
                                        ui.button("🎞️ Renderizar 9:16", on_click=make_render_handler()).classes("w-1/2 btn-gradient text-xs")
                                        ui.button("🚀 Publicar", on_click=lambda: ui.notify("Publicação agendada!")).classes("w-1/2 bg-[#2D313E] text-xs")

                    render_storyboards()

            # TAB 2: INGESTÃO
            with ui.tab_panel(tab_ingest).classes("w-full p-4 gap-4"):
                ui.label("📥 Ingestão por Link Direto do YouTube").classes("font-bold text-xl text-white")
                ui.label("Cole a URL do vídeo do YouTube para baixar o MP3 e registrar automaticamente no acervo do sistema.").classes("text-sm text-gray-400")

                with ui.card().classes("w-full bg-studio-panel p-6 rounded-xl gap-4 border border-[#2D313E]"):
                    input_url = ui.input("URL do YouTube:", placeholder="https://www.youtube.com/watch?v=...").classes("w-full")

                    def handle_ingest_click():
                        if not input_url.value:
                            ui.notify("Insira uma URL válida!", type="warning")
                            return
                        
                        ui.notify("🚀 Disparando download do áudio...", type="info")
                        try:
                            res = requests.post(f"{API_BASE_URL}/api/v1/ingest", json={"youtube_url": input_url.value}, timeout=120)
                            if res.status_code == 200:
                                ui.notify(f"✅ {res.json().get('file_name')} baixado com sucesso!", type="positive")
                            else:
                                ui.notify(f"Erro: {res.text}", type="negative")
                        except Exception as err:
                            ui.notify(f"Falha na API: {err}", type="negative")

                    ui.button("🚀 Importar Mídia para o Workspace", on_click=handle_ingest_click).classes("btn-gradient px-8 py-2")

            # TAB 3: MINERAÇÃO GEMINI
            with ui.tab_panel(tab_mining).classes("w-full p-4 gap-4"):
                ui.label("🧠 Mineração Teológica Direta de Áudios Locais").classes("font-bold text-xl text-white")
                ui.label("Processamento multimodal na nuvem do Google via Gemini 1.5 Flash File API (Zero consumo de RAM/GPU do seu PC).").classes("text-sm text-gray-400")

                audios_list = get_local_audios()
                grid_data = []
                for f in audios_list:
                    ins_f = insights_dir / f"{f.stem}.insights.json"
                    is_m = ins_f.exists() and ins_f.stat().st_size > 100
                    grid_data.append({
                        "Arquivo MP3": f.name,
                        "Tamanho MB": round(f.stat().st_size / (1024 * 1024), 2),
                        "Status": "🟢 MINERADO" if is_m else "🟡 PENDENTE"
                    })

                ui.table(
                    columns=[
                        {"name": "Arquivo MP3", "label": "Arquivo MP3", "field": "Arquivo MP3", "align": "left"},
                        {"name": "Tamanho MB", "label": "Tamanho (MB)", "field": "Tamanho MB", "align": "center"},
                        {"name": "Status", "label": "Status Mineração", "field": "Status", "align": "center"},
                    ],
                    rows=grid_data
                ).classes("w-full bg-studio-panel rounded-lg")


# Executa o Servidor Web do NiceGUI na Porta 8080
if __name__ in {"__main__", "__mp_main__"}:
    logger.info("Inicializando NiceGUI Studio App na porta 8080 (host=127.0.0.1)...")
    ui.run(
        title="IBPM CR - Studio Pro",
        host="127.0.0.1",
        port=8080,
        reload=False,
        dark=True,
        reconnect_timeout=10.0,
        storage_secret="ibpmcr_secret_key"
    )
