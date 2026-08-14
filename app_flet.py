"""
IBPM CR AUTOMATION STUDIO PRO - FLET (FLUTTER ENGINE FOR PYTHON).

Interface Desktop / Web Nativa de Alta Fidelidade Visual estilo DaVinci Resolve / CapCut Pro
desenvolvida em Flet (Flutter).

Execução no Terminal:
    python app_flet.py
"""

import sys
import os
import json
import requests
from pathlib import Path
from typing import Dict, Any, List

import flet as ft

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("FletStudioApp")

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")

audio_dir = Path("data/audio_podcasts")
insights_dir = Path("data/audio_podcasts/conteudos_fase3")
cuts_dir = Path("data/audio_podcasts/cortes_fase4")

audio_dir.mkdir(parents=True, exist_ok=True)
insights_dir.mkdir(parents=True, exist_ok=True)
cuts_dir.mkdir(parents=True, exist_ok=True)


def get_local_audios() -> List[Path]:
    """Retorna os áudios válidos no disco local."""
    return sorted([
        f for f in audio_dir.glob("*")
        if f.suffix.lower() in [".mp3", ".m4a", ".webm", ".mp4"] and not f.name.endswith(".part") and f.stat().st_size > 10000
    ])


def main(page: ft.Page):
    # Configuração de Tema do Flutter (Dark Mode CapCut)
    page.title = "IBPM CR - Studio Pro (Flutter Engine)"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0B0C10"
    page.padding = 0
    page.spacing = 0

    # -------------------------------------------------------------------------
    # TOP HEADER (FLUTTER APPBAR)
    # -------------------------------------------------------------------------
    header = ft.Container(
        content=ft.Row(
            controls=[
                ft.Row(
                    controls=[
                        ft.Icon(name=ft.Icons.MOVIE_OUTLINED, color="#F59E0B", size=30),
                        ft.Text("IBPM CR STUDIO PRO", size=20, weight=ft.FontWeight.BOLD, color="#F59E0B"),
                        ft.Container(
                            content=ft.Text("FLUTTER 60 FPS ENGINE", size=10, weight=ft.FontWeight.BOLD, color="#00D2FF"),
                            bgcolor="#1E222B",
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=12
                        )
                    ],
                    alignment=ft.MainAxisAlignment.START,
                    spacing=12
                ),
                ft.Row(
                    controls=[
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(name=ft.Icons.CLOUD_DONE, color="#10B981", size=16),
                                ft.Text("Gemini 1.5 Active", size=12, color="#10B981")
                            ]),
                            bgcolor="#064E3B",
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=8
                        ),
                        ft.Container(
                            content=ft.Row([
                                ft.Icon(name=ft.Icons.API, color="#3B82F6", size=16),
                                ft.Text("FastAPI :8000", size=12, color="#3B82F6")
                            ]),
                            bgcolor="#1E3A8A",
                            padding=ft.padding.symmetric(horizontal=10, vertical=5),
                            border_radius=8
                        )
                    ],
                    spacing=10
                )
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        bgcolor="#16181D",
        padding=ft.padding.symmetric(horizontal=20, vertical=12),
        border=ft.border.only(bottom=ft.BorderSide(1, "#262930"))
    )

    # -------------------------------------------------------------------------
    # STATE & CONTROLS FOR WORKSPACE
    # -------------------------------------------------------------------------
    audios = get_local_audios()
    audio_dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(f.name) for f in audios],
        value=audios[0].name if audios else "",
        label="Culto Ativo no Workspace",
        width=400,
        bgcolor="#16181D"
    )

    storyboard_grid = ft.Row(wrap=True, spacing=15, run_spacing=15)
    status_snack = ft.SnackBar(content=ft.Text(""))
    page.overlay.append(status_snack)

    def show_notify(msg: str, color: str = "#10B981"):
        status_snack.content = ft.Text(msg, color="#FFFFFF")
        status_snack.bgcolor = color
        status_snack.open = True
        page.update()

    def update_storyboards(e=None):
        storyboard_grid.controls.clear()
        if not audio_dropdown.value:
            storyboard_grid.controls.append(ft.Text("Nenhum áudio selecionado.", color="#9CA3AF"))
            page.update()
            return

        selected_stem = Path(audio_dropdown.value).stem
        ins_path = insights_dir / f"{selected_stem}.insights.json"

        if not ins_path.exists() or ins_path.stat().st_size < 100:
            storyboard_grid.controls.append(
                ft.Container(
                    content=ft.Column([
                        ft.Icon(name=ft.Icons.ANALYTICS_OUTLINED, size=48, color="#F59E0B"),
                        ft.Text("Nenhum relatório de cortes minerado para este culto ainda.", size=14, color="#9CA3AF"),
                        ft.Text("Clique no botão 'Minerar Teologia (Gemini)' para processar.", size=12, color="#6B7280")
                    ], alignment=ft.MainAxisAlignment.CENTER, horizontal_alignment=ft.CrossAxisAlignment.CENTER),
                    padding=30,
                    bgcolor="#16181D",
                    border_radius=12,
                    alignment=ft.alignment.center
                )
            )
            page.update()
            return

        with open(ins_path, "r", encoding="utf-8") as f:
            payload = json.load(f)

        short_cuts = payload.get("short_form_cuts", [])
        src_id = payload.get("source_video_id", "FlqCTPRsIT4")

        for idx, cut in enumerate(short_cuts, 1):
            cut_id = cut.get("cut_id") or f"short_{idx:03d}"
            
            def trigger_render(cut_payload=cut, c_id=cut_id, video_src=src_id):
                show_notify(f"🎞️ Renderizando {c_id} no FFmpeg...", "#3B82F6")
                try:
                    r = requests.post(
                        f"{API_BASE_URL}/api/v1/render",
                        json={
                            "cut_id": c_id,
                            "video_url": f"https://www.youtube.com/watch?v={video_src}",
                            "cut_payload": cut_payload,
                            "format_type": "9:16",
                            "start_sec": 0.0,
                            "end_sec": 45.0
                        },
                        timeout=300
                    )
                    if r.status_code == 200:
                        show_notify(f"✅ Corte {c_id} renderizado com sucesso!", "#10B981")
                    else:
                        show_notify(f"Erro na API: {r.text}", "#EF4444")
                except Exception as err:
                    show_notify(f"Falha na requisição: {err}", "#EF4444")

            card = ft.Container(
                content=ft.Column([
                    ft.Row([
                        ft.Text(f"🎬 Short #{idx}: {cut.get('title_hook_a')}", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF", width=300),
                        ft.Container(
                            content=ft.Text(cut.get("category", "Hook"), size=10, weight=ft.FontWeight.BOLD, color="#D47AFF"),
                            bgcolor="#2D1A3F",
                            padding=ft.padding.symmetric(horizontal=8, vertical=4),
                            border_radius=4
                        )
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
                    ft.Text(f"Hook B: {cut.get('title_hook_b')}", size=12, color="#9CA3AF", italic=True),
                    ft.Container(
                        content=ft.Column([
                            ft.Text(f"Início: {cut.get('start_anchor_7_words')}", size=11, color="#F59E0B", weight=ft.FontWeight.BOLD),
                            ft.Text(f"Fim: {cut.get('end_anchor_7_words')}", size=11, color="#F59E0B", weight=ft.FontWeight.BOLD)
                        ]),
                        bgcolor="#0F1117",
                        padding=8,
                        border_radius=6,
                        border=ft.border.all(1, "#262930")
                    ),
                    ft.Row([
                        ft.ElevatedButton(
                            "🎞️ Renderizar 9:16",
                            on_click=lambda e, cp=cut, cid=cut_id, vs=src_id: trigger_render(cp, cid, vs),
                            style=ft.ButtonStyle(bgcolor="#F59E0B", color="#000000")
                        ),
                        ft.OutlinedButton("🚀 Publicar", on_click=lambda e: show_notify("Publicação agendada!"))
                    ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN)
                ], spacing=10),
                width=450,
                bgcolor="#16181D",
                padding=15,
                border_radius=10,
                border=ft.border.all(1, "#262930")
            )
            storyboard_grid.controls.append(card)

        page.update()

    def trigger_mining(e):
        if not audio_dropdown.value:
            show_notify("Selecione um culto primeiro!", "#EF4444")
            return
        selected_file = audio_dropdown.value
        v_id = Path(selected_file).stem.split("_")[2] if len(Path(selected_file).stem.split("_")) > 2 else Path(selected_file).stem
        show_notify(f"📤 Enviando {selected_file} para a Gemini File API...", "#3B82F6")
        
        try:
            r = requests.post(
                f"{API_BASE_URL}/api/v1/process-gemini",
                json={"audio_file_path": selected_file, "video_id": v_id},
                timeout=180
            )
            if r.status_code == 200:
                show_notify("🎉 Mineração concluída com sucesso!", "#10B981")
                update_storyboards()
            else:
                show_notify(f"Erro na API: {r.text}", "#EF4444")
        except Exception as err:
            show_notify(f"Falha na API: {err}", "#EF4444")

    audio_dropdown.on_change = update_storyboards

    # -------------------------------------------------------------------------
    # MAIN WORKSPACE VIEW (TABS + CARDS + TIMELINE)
    # -------------------------------------------------------------------------
    top_control_bar = ft.Container(
        content=ft.Row([
            ft.Row([
                ft.Icon(name=ft.Icons.AUDIO_FILE, color="#F59E0B"),
                audio_dropdown
            ], spacing=10),
            ft.ElevatedButton(
                "🧠 Minerar Teologia (Gemini)",
                icon=ft.Icons.PSYCHOLOGY,
                on_click=trigger_mining,
                style=ft.ButtonStyle(bgcolor="#F59E0B", color="#000000")
            )
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),
        padding=15,
        bgcolor="#16181D",
        border_radius=10
    )

    timeline_box = ft.Container(
        content=ft.Column([
            ft.Text("🎚️ Timeline de Retenção Visual & Arcos Emocionais", size=14, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            ft.Row([
                ft.Container(content=ft.Text("HOOK (0-3s)", size=10, weight=ft.FontWeight.BOLD, color="#FFFFFF"), bgcolor="#EF4444", height=30, expand=2, alignment=ft.alignment.center, border_radius=4),
                ft.Container(content=ft.Text("CLÍMAX PENTECOSTAL / EXEGESE (3-45s)", size=10, weight=ft.FontWeight.BOLD, color="#000000"), bgcolor="#F59E0B", height=30, expand=8, alignment=ft.alignment.center, border_radius=4),
                ft.Container(content=ft.Text("CTA (45-60s)", size=10, weight=ft.FontWeight.BOLD, color="#000000"), bgcolor="#00D2FF", height=30, expand=2, alignment=ft.alignment.center, border_radius=4)
            ], spacing=4)
        ], spacing=8),
        padding=15,
        bgcolor="#16181D",
        border_radius=10
    )

    content_area = ft.Container(
        content=ft.Column([
            top_control_bar,
            timeline_box,
            ft.Text("🎞️ Storyboards de Cortes Virais Minerados", size=18, weight=ft.FontWeight.BOLD, color="#FFFFFF"),
            storyboard_grid
        ], spacing=20, scroll=ft.ScrollMode.AUTO),
        padding=20,
        expand=True
    )

    page.add(
        ft.Column([
            header,
            content_area
        ], expand=True, spacing=0)
    )

    update_storyboards()


if __name__ == "__main__":
    logger.info("Inicializando Flet App (Flutter Engine)...")
    ft.app(target=main)
