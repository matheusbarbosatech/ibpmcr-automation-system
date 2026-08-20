"""
PIPELINE DE MINERAÇÃO DA FASE 2 MINERAÇÃO (TEXTRANK + NMS + TIMESTAMPS EXATOS + PLAYLISTS)
IBPM CR AUTOMATION SYSTEM - Arquitetura Orientada a Objetos.
"""

import sys
import os
import json
import csv
import re
from pathlib import Path
import time
from typing import Dict, List, Tuple, Optional

try:
    from rich.console import Console
    from rich.live import Live
    from rich.panel import Panel
    from rich.table import Table
    from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
    from rich.layout import Layout
    from rich.text import Text
    HAS_RICH = True
except ImportError:
    HAS_RICH = False

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.services.minerador_nlp import DualSermonMiner, PlaylistOrganizer
from src.services.cortador_ffmpeg import FastStreamCopyCutter


class Fase2TerminalPainel:
    """
    Painel de Controle Limpo e Sem Cintilação para a Fase 2 Mineração.
    Imprime linhas sequenciais legíveis a cada evento e exibe um relatório final elegante.
    """

    def __init__(self, total_cultos: int, usar_painel: bool = True):
        self.total_cultos = total_cultos
        self.usar_painel = HAS_RICH and usar_painel
        self.start_time = time.time()
        self.sucessos = 0
        self.erros = 0
        self.total_shorts = 0
        self.total_mids = 0

        if self.usar_painel:
            self.console = Console()

    def start(self):
        if self.usar_painel:
            header_text = Text()
            header_text.append("🏛️  IBPM CR AUTOMATION SYSTEM — FASE 2 MINERAÇÃO SEMÂNTICA\n", style="bold yellow")
            header_text.append(f"• Total de Cultos   : {self.total_cultos} transcrições\n", style="bold white")
            header_text.append("• Engine de Mineração: TextRank Extrativo + Heurística Pentecostal 50+ + NMS Temporal\n", style="bold green")
            header_text.append("• Clusterização     : MiniBatchKMeans / Playlists Temáticas Automáticas", style="dim white")
            self.console.print(Panel(header_text, border_style="yellow", expand=False))
            self.console.print("[dim cyan]──────── Minando Transcrições e Gerando Relatório ────────[/dim cyan]\n")

    def registrar_culto(self, sermon_id: str, num_shorts: int, num_mids: int, score_max: float, status: str = "OK"):
        if status == "OK":
            self.sucessos += 1
        else:
            self.erros += 1

        self.total_shorts += num_shorts
        self.total_mids += num_mids

        atual = self.sucessos + self.erros
        pct = (atual / self.total_cultos) * 100
        elapsed_sec = time.time() - self.start_time
        elapsed_str = time.strftime("%M:%S", time.gmtime(elapsed_sec))

        if self.usar_painel:
            st_badge = "[bold green]✅ OK[/bold green]" if status == "OK" else "[bold red]❌ ERRO[/bold red]"

            line = Text()
            line.append(f"[{atual:03d}/{self.total_cultos:03d}] ", style="bold bright_white")
            line.append(f"({pct:5.1f}%) ", style="bold yellow")
            line.append(f"{st_badge} ", style="bold")
            line.append(f"• {sermon_id[:42]:<42} ", style="white")
            line.append(f"| Shorts: {num_shorts:02d} ", style="green")
            line.append(f"| Mids: {num_mids:02d} ", style="magenta")
            line.append(f"| Score: {score_max:.3f} ", style="bright_yellow")
            line.append(f"| Tempo: {elapsed_str}", style="dim")

            self.console.print(line)
        else:
            print(f"[{atual:03d}/{self.total_cultos:03d}] ({pct:.1f}%) {status} -> {sermon_id} (Shorts: {num_shorts} | Mids: {num_mids})")

    def stop(self):
        elapsed_sec = time.time() - self.start_time
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed_sec))
        total_cortes = self.total_shorts + self.total_mids

        if self.usar_painel:
            t = Table(show_header=True, header_style="bold yellow", box=None, padding=(0, 2))
            t.add_column("📄 Cultos Processados", justify="center", style="bold white")
            t.add_column("✂️ Shorts (9:16)", justify="center", style="bold green")
            t.add_column("🎬 Mídias (16:9)", justify="center", style="bold magenta")
            t.add_column("📊 Cortes Totais", justify="center", style="bold yellow")
            t.add_column("⏱️ Tempo Total", justify="center", style="bold white")

            t.add_row(
                f"{self.sucessos} / {self.total_cultos}",
                str(self.total_shorts),
                str(self.total_mids),
                str(total_cortes),
                elapsed_str
            )

            self.console.print("\n[dim cyan]────────────────────────────────────────────[/dim cyan]")
            self.console.print(Panel(t, title="[bold bright_green] 🎉 RESUMO FINAL DA MINERAÇÃO FASE 2 [/bold bright_green]", border_style="green", expand=False))


class PipelineMineracaoFase2:
    """
    Classe orquestradora da Fase 2 Mineração: Mineração Teológica/Extrativa, Clusterização e Cortes de Mídia.
    """

    EXTENSOES_MIDIA = {".webm", ".mp4", ".mkv", ".mp3", ".wav", ".m4a"}

    def __init__(self, output_dir: Optional[Path] = None, filtro: Optional[str] = None, usar_painel: bool = True):
        self.logger = get_logger("PipelineFase2Mineracao")
        self.miner = DualSermonMiner()
        self.cutter = FastStreamCopyCutter()
        self.filtro = filtro
        self.usar_painel = usar_painel

        # Definição de caminhos para a Fase 2 Mineração
        self.pasta_base = BASE_DIR / "data" / "fase2_mineracao"
        
        self.dir_audios_candidatos = [
            BASE_DIR / "data" / "audios",
            BASE_DIR / "data" / "fase1_mapeamento" / "audios",
            BASE_DIR / "data" / "1.AUDIOS",
        ]
        
        self.dir_transcricoes_candidatos = [
            BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes" / "txt",
            BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes" / "json",
            BASE_DIR / "data" / "transcriptions" / "txt",
            BASE_DIR / "data" / "transcriptions" / "json",
            BASE_DIR / "data" / "1.TRANSCRICOES",
        ]

        if output_dir:
            self.dir_output = Path(output_dir).resolve()
        else:
            self.dir_output = self.pasta_base

        self.dir_insights = self.dir_output / "insights_json"
        self.dir_cortes = self.dir_output / "cortes_finais"
        self.arq_csv = self.dir_output / "relatorio_cortes.csv"
        self.arq_playlists = self.dir_output / "playlists_tematicas.json"


        # Listas de estado em memória
        self.todos_cortes_csv: List[dict] = []
        self.cortes_medios_playlists: List[dict] = []

    def preparar_diretorios(self):
        """Garante que toda a estrutura de pastas de saída exista."""
        for diretorio in [self.dir_output, self.dir_insights, self.dir_cortes]:
            diretorio.mkdir(parents=True, exist_ok=True)

    def extrair_yt_id(self, nome_arquivo: str) -> str:
        """Extrai o ID do YouTube (11 caracteres) ignorando prefixos numéricos."""
        match = re.search(r"([a-zA-Z0-9_-]{11})", Path(nome_arquivo).stem)
        return match.group(1) if match else Path(nome_arquivo).stem

    def mapear_acervo(self) -> Tuple[Dict[str, Path], Dict[str, Path]]:
        """
        Mapeia os arquivos agrupando pelo ID do YouTube buscando nos diretórios candidatos.
        """
        mapa_transcricoes_bruto = {}
        mapa_midias_bruto = {}
        nomes_originais = {}

        # 1. Mapeamento de Mídias (Áudios)
        for dir_audio in self.dir_audios_candidatos:
            if dir_audio.exists():
                for arq in dir_audio.iterdir():
                    if arq.is_file() and arq.suffix.lower() in self.EXTENSOES_MIDIA:
                        yt_id = self.extrair_yt_id(arq.name)
                        if yt_id not in mapa_midias_bruto:
                            mapa_midias_bruto[yt_id] = arq
                            nomes_originais[yt_id] = arq.stem

        # 2. Mapeamento de Transcrições
        formatos_texto = {".txt", ".srt", ".vtt"}
        for dir_trans in self.dir_transcricoes_candidatos:
            if dir_trans.exists():
                for arq in dir_trans.iterdir():
                    if arq.is_file():
                        ext = arq.suffix.lower()
                        yt_id = self.extrair_yt_id(arq.name)
                        
                        if ext in formatos_texto:
                            if yt_id not in mapa_transcricoes_bruto:
                                mapa_transcricoes_bruto[yt_id] = arq
                        elif ext == ".json" and not arq.name.endswith(".insights.json"):
                            # O JSON tem prioridade sobre TXT/SRT/VTT
                            mapa_transcricoes_bruto[yt_id] = arq

        # 2.5 Carrega Filtro de Qualidade de Mídia (se existir relatorio_qualidade_midias.json)
        desqualificados_ids = set()
        qual_json = BASE_DIR / "data" / "fase1_mapeamento" / "relatorio_qualidade_midias.json"
        if qual_json.exists():
            try:
                with open(qual_json, "r", encoding="utf-8") as f_q:
                    q_data = json.load(f_q)
                    for item in q_data:
                        if item.get("status") == "DESQUALIFICADO":
                            desqualificados_ids.add(item.get("video_id"))
            except Exception:
                pass

        # 3. Consolidação Final
        mapa_final_transcricoes = {}
        mapa_final_midias = {}
        
        for yt_id, arq_trans in mapa_transcricoes_bruto.items():
            if yt_id in desqualificados_ids:
                continue

            sermon_id = nomes_originais.get(yt_id, arq_trans.stem)
            mapa_final_transcricoes[sermon_id] = arq_trans
            
            if yt_id in mapa_midias_bruto:
                mapa_final_midias[sermon_id] = mapa_midias_bruto[yt_id]
                
        return mapa_final_transcricoes, mapa_final_midias


    def carregar_transcricao(self, caminho: Path) -> Tuple[str, List[dict]]:
        """Lê de forma segura JSON, TXT, SRT ou VTT com parser agressivo e fallback para TXT."""
        ext = caminho.suffix.lower()
        try:
            if ext == ".json":
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                    
                texto = ""
                segmentos = []
                
                if isinstance(dados, dict):
                    texto = dados.get("text", "") or dados.get("texto", "")
                    segmentos = dados.get("segments", []) or dados.get("segmentos", []) or dados.get("transcript", []) or dados.get("transcricao", [])
                    
                    if not texto and segmentos and isinstance(segmentos, list):
                        texto = " ".join(s.get("text", "") if isinstance(s, dict) else str(s) for s in segmentos)
                        
                elif isinstance(dados, list):
                    segmentos = dados
                    texto = " ".join(s.get("text", "") if isinstance(s, dict) else str(s) for s in dados)
                
                if not texto.strip():
                    txt_fallback = BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes" / "txt" / f"{caminho.stem}.txt"
                    if txt_fallback.exists():
                        with open(txt_fallback, "r", encoding="utf-8", errors="ignore") as f_txt:
                            texto = f_txt.read().strip()
                
                return texto.strip(), segmentos if isinstance(segmentos, list) else []
                    
            elif ext in {".txt", ".srt", ".vtt"}:
                with open(caminho, "r", encoding="utf-8", errors="ignore") as f:
                    conteudo = f.read()
                    
                if ext in {".srt", ".vtt"}:
                    conteudo = re.sub(r'^WEBVTT.*\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'^\d+$\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'^\d{2}:\d{2}:\d{2}.*-->.*\n', '', conteudo, flags=re.MULTILINE)
                    conteudo = re.sub(r'\n+', ' ', conteudo)
                    
                return conteudo.strip(), []
                
        except Exception:
            pass
            
        return "", []

    def executar(self):
        self.preparar_diretorios()
        mapa_trans, mapa_midias = self.mapear_acervo()

        if self.filtro:
            mapa_trans = {k: v for k, v in mapa_trans.items() if self.filtro in k or self.filtro in v.name}
            mapa_midias = {k: v for k, v in mapa_midias.items() if k in mapa_trans}

        if not mapa_trans:
            print("⚠️ Nenhuma transcrição encontrada com os filtros atuais. Encerrando pipeline.")
            return

        total_cultos = len(mapa_trans)
        painel = Fase2TerminalPainel(total_cultos=total_cultos, usar_painel=self.usar_painel)
        painel.start()

        try:
            for idx, (sermon_id, caminho_arq) in enumerate(mapa_trans.items(), 1):
                texto, segmentos = self.carregar_transcricao(caminho_arq)
                if not texto or len(texto) < 50:
                    painel.registrar_culto(sermon_id, 0, 0, 0.0, status="ERRO")
                    continue

                try:
                    caminho_audio = mapa_midias.get(sermon_id)
                    insights = self.miner.mine_sermon(
                        transcript_text=texto,
                        sermon_id=sermon_id,
                        audio_path=str(caminho_audio) if caminho_audio else None
                    )

                    out_json = self.dir_insights / f"{sermon_id}.insights.json"
                    with open(out_json, "w", encoding="utf-8") as f:
                        json.dump(insights, f, ensure_ascii=False, indent=2)

                    shorts = insights.get("short_form_cuts", [])
                    mids = insights.get("mid_form_cuts", [])
                    
                    for s in shorts:
                        s.update({"sermon_id": sermon_id, "tipo": "Short (9:16)"})
                        self.todos_cortes_csv.append(s)
                        
                    for m in mids:
                        m.update({"sermon_id": sermon_id, "tipo": "Mid (16:9)"})
                        self.todos_cortes_csv.append(m)
                        self.cortes_medios_playlists.append(m)

                    top_score = max([s.get("score", 0.0) for s in shorts + mids], default=0.0)
                    painel.registrar_culto(sermon_id, len(shorts), len(mids), top_score, status="OK")

                except Exception as e:
                    painel.registrar_culto(sermon_id, 0, 0, 0.0, status="ERRO")

        finally:
            painel.stop()

        self._gerar_artefatos(painel.sucessos, total_cultos)

    def _gerar_artefatos(self, sucessos: int, total: int):
        print("\n" + "─" * 75)
        
        # 1. Gerar Relatório CSV
        if self.todos_cortes_csv:
            campos = ["sermon_id", "tipo", "start_sec", "end_sec", "duracao", "score", "titulo", "texto_trecho"]
            with open(self.arq_csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                for c in self.todos_cortes_csv:
                    st = float(c.get("start_sec", c.get("start", c.get("start_time", 0))))
                    et = float(c.get("end_sec", c.get("end", c.get("end_time", 0))))
                    writer.writerow({
                        "sermon_id": c.get("sermon_id", ""),
                        "tipo": c.get("tipo", ""),
                        "start_sec": round(st, 2),
                        "end_sec": round(et, 2),
                        "duracao": round(et - st, 2),
                        "score": round(float(c.get("score", 0)), 3),
                        "titulo": c.get("title_hook_a", c.get("titulo", c.get("title", "Corte Automático"))),
                        "texto_trecho": c.get("text_snippet", c.get("text", c.get("texto", ""))).replace("\n", " ")
                    })
            print(f"📊 Relatório CSV exportado: '{self.arq_csv}' ({len(self.todos_cortes_csv)} cortes).")

        # 2. Gerar Playlists Temáticas (Clustering)
        if self.cortes_medios_playlists:
            try:
                k = max(1, min(5, len(self.cortes_medios_playlists)))
                organizer = PlaylistOrganizer(num_playlists=k)
                playlists = organizer.build_playlists(self.cortes_medios_playlists)
                with open(self.arq_playlists, "w", encoding="utf-8") as f:
                    json.dump(playlists, f, ensure_ascii=False, indent=2)
                print(f"🎶 Playlists temáticas salvas em: '{self.arq_playlists}'.")
            except Exception as e:
                print(f"⚠️ Erro no agrupamento de playlists: {e}")

        # Resumo Executivo
        print("\n" + "=" * 75)
        print("                       🎉 MINERAÇÃO FASE 2 FINALIZADA")
        print("=" * 75)
        print(f"  • Cultos Minerados com Sucesso : {sucessos} de {total}")
        print(f"  • Total de Cortes Mapeados     : {len(self.todos_cortes_csv)}")
        print(f"  • Pasta de Resultados Entrega  : {self.dir_output}")
        print("=" * 75 + "\n")


PipelineMineracaoFase3 = PipelineMineracaoFase2

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline Fase 2 Mineração IBPM CR Automation")
    parser.add_argument("--filtro", "--arquivo", type=str, default=None, help="Filtra transcrição por prefixo ou ID (ex: 001)")
    parser.add_argument("--output-dir", type=str, default=None, help="Diretório customizado de saída")
    parser.add_argument("--no-painel", action="store_true", help="Desativa o painel Rich no terminal (modo texto padrão)")
    args = parser.parse_args()

    pipeline = PipelineMineracaoFase2(
        output_dir=args.output_dir,
        filtro=args.filtro,
        usar_painel=not args.no_painel
    )
    pipeline.executar()

