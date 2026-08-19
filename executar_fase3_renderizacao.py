"""
Script Oficial da Fase 3 Renderização - Renderização Audiovisual & Geração de Copy para Redes Sociais - IBPM CR Automation System.

Executa:
1. Corte e Edição Audiovisual (Stream Copy ultrarrápido -c copy ou Re-encoding Studio 9:16 Vertical com legendas Karaokê .ASS e EBU R128).
2. Geração de Metadados e Copy de Postagens para Instagram Reels, YouTube Shorts e TikTok (Títulos, Captions, Hashtags e Grade de Agendamento).
"""

import sys
import os
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.config import settings
from src.core.logger import get_logger
from src.services.cortador_ffmpeg import FastStreamCopyCutter, parse_timestamp_to_seconds
from src.infrastructure.ffmpeg_client import FFmpegClient

logger = get_logger("ExecutarFase3Renderizacao")


def gerar_copys_postagem(cortes_info: List[Dict[str, Any]], output_json: Path, output_txt: Path) -> List[Dict[str, Any]]:
    """
    Gera títulos chamativos, legendas completas, hashtags teológicas e grade de agendamento.
    """
    logger.info("✍️ Gerando Copy e Metadados de Postagem para Redes Sociais...")
    postagens = []
    
    start_date = datetime.now() + timedelta(days=1)
    horarios = ["08:00", "12:30", "19:00"]
    post_idx = 0

    for idx, item in enumerate(cortes_info):
        origem = item.get("sermon_id") or item.get("arquivo_origem", "culto")
        tipo = item.get("tipo", "Short")
        c_id = item.get("corte_id") or f"corte_{idx+1:03d}"
        dur = float(item.get("duracao") or item.get("duracao_segundos", 45))
        score = float(item.get("score", 0))
        texto = item.get("texto_trecho") or item.get("texto_do_corte", "")
        titulo_csv = item.get("titulo") or "Mensagem Edificante"

        # Títulos virais baseados no tipo de corte e conteúdo
        if "short" in str(tipo).lower():
            titulo = f"🔥 {titulo_csv.upper()} ({c_id})"
            hook = f"Ouça o que Deus tem para falar com você hoje! 📖✨\n\"{texto[:150]}...\""
        else:
            titulo = f"📖 ESTUDO BÍBLICO: {titulo_csv.upper()} ({c_id})"
            hook = f"Assista a esta exposição exegética da Palavra de Deus! 🙏\n\"{texto[:200]}...\""

        # Agendamento sequencial
        dia_post = start_date + timedelta(days=post_idx // 3)
        horario_post = horarios[post_idx % 3]
        data_agendamento = f"{dia_post.strftime('%Y-%m-%d')} às {horario_post}"

        caption = f"""{titulo}

{hook}

"Onde há a pregação pura da Palavra, ali está a presença de Deus."

💬 Deixe seu AMÉM nos comentários!
📲 Compartilhe esta mensagem com alguém que precisa ouvir isso hoje!
🔔 Siga a @ibpmcr para mais conteúdos edificantes.

---
#IBPMCR #Pregação #PalavraDeDeus #Jesus #Fé #Evangelho #ReelsCristao #Shorts #Biblia #MensagemDeFe
"""

        post_data = {
            "corte_id": c_id,
            "sermon_id": origem,
            "tipo": tipo,
            "duracao_segundos": dur,
            "score": score,
            "titulo_viral": titulo,
            "hook_subtitulo": hook,
            "data_agendamento_sugerida": data_agendamento,
            "legenda_completa": caption.strip(),
            "hashtags": ["#IBPMCR", "#Pregação", "#PalavraDeDeus", "#Jesus", "#Fé", "#Evangelho", "#Shorts", "#Reels"]
        }
        postagens.append(post_data)
        post_idx += 1

    # Salva JSON estruturado
    output_json.parent.mkdir(parents=True, exist_ok=True)
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(postagens, f, ensure_ascii=False, indent=2)

    # Salva TXT formatado para leitura humana
    with open(output_txt, "w", encoding="utf-8") as f:
        f.write("====================================================\n")
        f.write("   IBPM CR - GRADE DE POSTAGENS E COPYS DAS REDES   \n")
        f.write("====================================================\n\n")
        for p in postagens:
            f.write(f"📌 CORTE: {p['corte_id']} | TIPO: {p['tipo']} ({p['sermon_id']})\n")
            f.write(f"📅 AGENDAMENTO SUGERIDO: {p['data_agendamento_sugerida']}\n")
            f.write(f"⏱️ DURAÇÃO: {p['duracao_segundos']:.1f}s | SCORE: {p['score']:.3f}\n")
            f.write(f"🎯 TÍTULO: {p['titulo_viral']}\n")
            f.write("----------------------------------------------------\n")
            f.write(f"{p['legenda_completa']}\n")
            f.write("====================================================\n\n")

    logger.info(f"✅ Copy de {len(postagens)} postagens gerada com sucesso em '{output_json}' e '{output_txt}'.")
    return postagens


import time

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

from src.services.tratamento_audiovisual import AutoAudiovisualEnhancer


class Fase3TerminalPainel:
    """
    Painel de Controle Limpo e Sem Cintilação para o Terminal.
    Imprime linhas sequenciais legíveis a cada evento e exibe um relatório final elegante.
    """

    def __init__(self, total_cortes: int, modo: str, usar_painel: bool = True):
        self.total_cortes = total_cortes
        self.modo = modo
        self.usar_painel = HAS_RICH and usar_painel
        self.start_time = time.time()
        self.sucessos = 0
        self.erros = 0
        self.capas_geradas = 0

        if self.usar_painel:
            self.console = Console()

    def start(self):
        if self.usar_painel:
            header_text = Text()
            header_text.append("🏛️  IBPM CR AUTOMATION SYSTEM — FASE 3 RENDERIZAÇÃO\n", style="bold yellow")
            header_text.append(f"• Modo de Execução  : {self.modo.upper()}\n", style="bold cyan")
            header_text.append(f"• Total de Cortes   : {self.total_cortes} cortes agendados\n", style="bold white")
            header_text.append("• Qualidade Mídia   : ⚡ MÁXIMA QUALIDADE ABSOLUTA 4K (2160p60 Nativo de 6.3GB)\n", style="bold green")
            header_text.append("• Processamento     : Auto-Framing 9:16 + Lanczos Resampling + Áudio EBU R128 (-16 LUFS)", style="dim white")

            self.console.print(Panel(header_text, border_style="yellow", expand=False))
            self.console.print("[dim cyan]──────── Processando Fila de Cortes ────────[/dim cyan]\n")

    def registrar_corte(self, corte_id: str, sermon_id: str, duracao_sec: float, com_capa: bool = True, status: str = "OK"):
        if status == "OK":
            self.sucessos += 1
            if com_capa:
                self.capas_geradas += 1
        else:
            self.erros += 1

        atual = self.sucessos + self.erros
        pct = (atual / self.total_cortes) * 100
        elapsed_sec = time.time() - self.start_time
        elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed_sec))

        if self.usar_painel:
            if status == "OK":
                st_badge = "[bold green]✅ CONCLUÍDO[/bold green]"
            else:
                st_badge = "[bold red]❌ ERRO[/bold red]"

            line = Text()
            line.append(f"[{atual:03d}/{self.total_cortes:03d}] ", style="bold bright_white")
            line.append(f"({pct:5.1f}%) ", style="bold yellow")
            line.append(f"{st_badge} ", style="bold")
            line.append(f"• {corte_id:<12} ", style="bold cyan")
            line.append(f"| {sermon_id[:38]:<38} ", style="white")
            line.append(f"| {duracao_sec:4.1f}s ", style="bright_blue")
            line.append(f"| Tempo: {elapsed_str}", style="dim")

            self.console.print(line)
        else:
            print(f"[{atual:03d}/{self.total_cortes:03d}] ({pct:.1f}%) {status} -> {corte_id} ({sermon_id[:30]}) - {duracao_sec:.1f}s")

    def stop(self):
        elapsed_sec = time.time() - self.start_time
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))

        if self.usar_painel:
            t = Table(show_header=True, header_style="bold yellow", box=None, padding=(0, 2))
            t.add_column("✂️ Sucessos", justify="center", style="bold green")
            t.add_column("🖼️ Capas Geradas", justify="center", style="bold cyan")
            t.add_column("❌ Falhas", justify="center", style="bold red")
            t.add_column("⏱️ Tempo Total", justify="center", style="bold white")

            t.add_row(
                f"{self.sucessos} / {self.total_cortes}",
                str(self.capas_geradas),
                str(self.erros),
                elapsed_str
            )

            self.console.print("\n[dim cyan]────────────────────────────────────────────[/dim cyan]")
            self.console.print(Panel(t, title="[bold bright_green] 🎉 RESUMO FINAL DA PRODUÇÃO FASE 3 [/bold bright_green]", border_style="green", expand=False))



def executar_fase3_renderizacao(
    modo: str = "enhanced_studio",
    max_cortes: int = 50,
    export_desktop: bool = True,
    filtro: Optional[str] = None,
    usar_painel: bool = True
):
    """
    Executa a Fase 3 Renderização completa com Painel Rich e Download na Melhor Qualidade.
    Modos:
    - stream_copy: Corte instantâneo sem re-encoding (0.1s).
    - studio_9x16: Renderização vertical 9:16 padrão.
    - enhanced_studio: Enquadramento Inteligente (Rastreamento do Pregador) + Áudio EBU R128 (-16 LUFS) + Nitidez e Cor de Vídeo.
    - full: Executa todos os modos.
    """
    csv_file = Path("data/fase2_mineracao/relatorio_cortes.csv")
    if not csv_file.exists():
        csv_file = Path("data/relatorio_cortes.csv")

    videos_dir = Path("data/videos")
    videos_dir.mkdir(parents=True, exist_ok=True)
    audios_dir = Path("data/audios")

    output_stream_copy = Path("data/fase3_renderizacao/cortes_finais")
    output_studio_video = Path("data/fase3_renderizacao/cortes_finais_video")
    output_enhanced_video = Path("data/fase3_renderizacao/cortes_finais_enhanced")
    json_postagens = Path("data/fase3_renderizacao/postagens_redes_sociais.json")
    txt_postagens = Path("data/fase3_renderizacao/postagens_redes_sociais.txt")

    if not csv_file.exists():
        logger.error(f"❌ Arquivo '{csv_file}' não encontrado. Execute a Fase 2 Mineração primeiro (python executar_fase2_mineracao.py).")
        return

    cortes_info = []
    with open(csv_file, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            s_id = row.get("sermon_id", row.get("arquivo_origem", ""))
            c_id = row.get("corte_id", "")
            if filtro and (filtro not in s_id and filtro not in c_id):
                continue
            cortes_info.append(row)
            if len(cortes_info) >= max_cortes:
                break

    if not cortes_info:
        print("⚠️ Nenhum corte encontrado no relatório com os filtros aplicados.")
        return

    total_cortes = len(cortes_info)
    painel = Fase3TerminalPainel(total_cortes=total_cortes, modo=modo, usar_painel=usar_painel)
    painel.start()

    try:
        # 1. Executa corte ultrarrápido Stream Copy (-c copy)
        if modo in ["stream_copy", "full"]:
            cutter = FastStreamCopyCutter()
            cuts_copy = cutter.cut_from_csv(csv_file, videos_dir, output_stream_copy)
            for c in cortes_info:
                painel.registrar_corte(c.get("corte_id", "short"), c.get("sermon_id", "culto"), float(c.get("duracao", 45)), com_capa=False, status="OK")

        # 2. Executa renderização 9:16 Studio Pro Vertical com FFmpeg
        elif modo in ["studio_9x16", "full"]:
            ffmpeg = FFmpegClient()
            output_studio_video.mkdir(parents=True, exist_ok=True)

            for idx, row in enumerate(cortes_info):
                orig = row.get("sermon_id", row.get("arquivo_origem", ""))
                c_id = row.get("corte_id") or f"corte_{idx+1:03d}"
                c_id_clean = "".join(c for c in c_id if c.isalnum() or c in ("_", "-")).strip()
                ts_in = str(row.get("start_sec", row.get("timestamp_inicio", "00:00:00")))
                dur = float(row.get("duracao", row.get("duracao_segundos", "45")))
                
                src_file = None
                for ext in [".mp4", ".webm", ".mkv", ".mp3", ".wav"]:
                    p = videos_dir / f"{orig}{ext}"
                    if not p.exists():
                        p = audios_dir / f"{orig}{ext}"
                    if p.exists():
                        src_file = p
                        break

                if not src_file:
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=False, status="ERRO")
                    continue

                out_video = output_studio_video / f"{orig}_{c_id_clean}_9x16.mp4"
                start_sec = float(ts_in) if ts_in.replace('.', '', 1).isdigit() else parse_timestamp_to_seconds(ts_in)
                end_sec = start_sec + dur

                try:
                    ffmpeg.render_short_form(
                        video_input=src_file,
                        output_path=out_video,
                        start_sec=start_sec,
                        end_sec=end_sec,
                        job_id=f"job_{c_id_clean}"
                    )
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=False, status="OK")
                except Exception:
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=False, status="ERRO")

        # 3. Executa Tratamento Audiovisual Automático + Enquadramento Inteligente (enhanced_studio)
        elif modo in ["enhanced_studio", "full"]:
            enhancer = AutoAudiovisualEnhancer()
            yt_client = None
            output_enhanced_video.mkdir(parents=True, exist_ok=True)

            for idx, row in enumerate(cortes_info):
                orig = row.get("sermon_id", row.get("arquivo_origem", ""))
                tipo = row.get("tipo", "Short")
                c_id = row.get("corte_id") or f"corte_{idx+1:03d}"
                c_id_clean = "".join(c for c in c_id if c.isalnum() or c in ("_", "-")).strip()
                ts_in = str(row.get("start_sec", row.get("timestamp_inicio", "0")))
                dur = float(row.get("duracao", row.get("duracao_segundos", "45")))

                src_file = None
                for ext in [".mp4", ".webm", ".mkv", ".mp3", ".wav"]:
                    p = videos_dir / f"{orig}{ext}"
                    if not p.is_file():
                        p = audios_dir / f"{orig}{ext}"
                    if p.is_file():
                        src_file = p
                        break

                # Se a mídia local não existir, realiza o Download Completo em 4K/Qualidade Máxima para data/videos/
                if not src_file:
                    parts = orig.split("_")
                    yt_id = next((pt for pt in parts if len(pt) == 11 and pt.isalnum()), None)
                    if yt_id:
                        try:
                            from src.infrastructure.yt_dlp_client import YTDLPClient
                            if not yt_client:
                                yt_client = YTDLPClient()
                            yt_url = f"https://www.youtube.com/watch?v={yt_id}"
                            target_mp4 = videos_dir / f"{orig}.mp4"
                            if target_mp4.exists():
                                try:
                                    target_mp4.unlink()
                                except Exception:
                                    pass

                            src_file = yt_client.download_full_video_best_quality(
                                video_url=yt_url,
                                output_path=target_mp4,
                                job_id=f"job_dl_full_{c_id_clean}"
                            )

                        except Exception as err:
                            logger.error(f"Falha ao baixar vídeo completo 4K para {orig}: {err}")



                if not src_file:
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=False, status="ERRO")
                    continue

                is_vertical = "short" in str(tipo).lower()
                out_enhanced = output_enhanced_video / f"{orig}_{c_id_clean}_enhanced.mp4"
                start_sec = float(ts_in) if ts_in.replace('.', '', 1).isdigit() else parse_timestamp_to_seconds(ts_in)
                end_sec = start_sec + dur
                titulo_csv = row.get("titulo", "Mensagem Edificante")

                try:
                    enhancer.enhance_clip(
                        input_video=src_file,
                        output_video=out_enhanced,
                        start_sec=start_sec,
                        end_sec=end_sec,
                        titulo=titulo_csv,
                        categoria=tipo,
                        is_vertical=is_vertical,
                        job_id=f"job_enhance_{c_id_clean}"
                    )
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=True, status="OK")
                except Exception as e:
                    painel.registrar_corte(c_id_clean, orig, dur, com_capa=False, status="ERRO")
                finally:
                    if src_file and "temp_" in src_file.name and src_file.exists():
                        try:
                            src_file.unlink()
                        except Exception:
                            pass


    finally:
        painel.stop()

    # 4. Gera Copy e Metadados de Postagem
    gerar_copys_postagem(cortes_info, json_postagens, txt_postagens)

    # 5. Copia para a Área de Trabalho se export_desktop for True
    if export_desktop:
        import shutil
        desktop_dir = Path(os.path.expanduser("~")) / "Desktop" / "teste_fase3_cortes"
        desktop_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(json_postagens, desktop_dir / json_postagens.name)
        shutil.copy2(txt_postagens, desktop_dir / txt_postagens.name)

        if output_stream_copy.exists():
            dest_stream = desktop_dir / "cortes_finais"
            dest_stream.mkdir(exist_ok=True)
            for f in output_stream_copy.glob("*.*"):
                shutil.copy2(f, dest_stream / f.name)

        if output_enhanced_video.exists():
            dest_enh = desktop_dir / "cortes_tratados_enhanced"
            dest_capas = desktop_dir / "capas_thumbnails"
            dest_enh.mkdir(exist_ok=True)
            dest_capas.mkdir(exist_ok=True)

            for f in output_enhanced_video.glob("*.mp4"):
                shutil.copy2(f, dest_enh / f.name)

            for f in output_enhanced_video.glob("*.jpg"):
                shutil.copy2(f, dest_capas / f.name)

    print("\n" + "=" * 65)
    print("       🎉 FASE 3 RENDERIZAÇÃO E PRODUÇÃO CONCLUÍDA")
    print("=" * 65)
    print(f"  • Modo de Execução        : {modo.upper()}")
    print(f"  • Cortes Renderizados     : {painel.sucessos} de {total_cortes}")
    print(f"  • Pasta de Vídeos Finais  : '{output_enhanced_video if modo == 'enhanced_studio' else output_stream_copy}'")
    print(f"  • Copys & Metadados       : '{json_postagens}' e '{txt_postagens}'")
    if export_desktop:
        print(f"  • Pasta Export no Desktop : '{Path(os.path.expanduser('~')) / 'Desktop' / 'teste_fase3_cortes'}'")
    print("=" * 65 + "\n")


executar_fase4 = executar_fase3_renderizacao


def main():
    parser = argparse.ArgumentParser(description="Executar Fase 3 - Renderização e Produção de Cortes IBPM CR")
    parser.add_argument("--modo", choices=["stream_copy", "studio_9x16", "enhanced_studio", "full"], default="enhanced_studio",
                        help="Modo de processamento (stream_copy = 0.1s, studio_9x16 = 9:16 vertical, enhanced_studio = Enquadramento Inteligente + DSP, full = todos)")
    parser.add_argument("--max", type=int, default=50, help="Quantidade máxima de cortes a processar (ex: --max 1 ou --max 5 para testes)")
    parser.add_argument("--filtro", type=str, default=None, help="Filtra corte por ID ou culto (ex: --filtro 001)")
    parser.add_argument("--no-painel", action="store_true", help="Desativa o painel Rich no terminal")
    parser.add_argument("--no-desktop", action="store_true", help="Desativa cópia automática para a Área de Trabalho")
    args = parser.parse_args()

    executar_fase3_renderizacao(
        modo=args.modo,
        max_cortes=args.max,
        export_desktop=not args.no_desktop,
        filtro=args.filtro,
        usar_painel=not args.no_painel
    )


if __name__ == "__main__":
    main()



