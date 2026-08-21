#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
PIPELINE UNIFICADO DA FASE 2 — MINERAÇÃO SEMÂNTICA, TRIAGEM QA (AQC) E FATIAMENTO DE ÁUDIO
IBPM CR AUTOMATION SYSTEM — Arquitetura Orientada a Objetos

Descrição:
  Este script unifica toda a Fase 2 em um único ponto de execução:
  1. Ingestão de Transcrições (JSON, TXT, VTT, SRT) e Mapeamento de Mídias.
  2. Mineração NLP Teológica (TextRank, NMS, Filtro Estrito de Louvor/Oração e Sentido Completo).
  3. Agrupamento de Playlists Temáticas (MiniBatchKMeans).
  4. Triagem de QA Automática (FFmpeg seek com padding 0.3s, librosa DSP, spaCy NLP).
  5. Exportação Unificada em `data/fase2_mineracao/` (aprovados vs rejeitados).
"""

import sys
import os
import json
import csv
import re
import time
import subprocess
import shutil
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

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

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.services.minerador_nlp import DualSermonMiner, PlaylistOrganizer
from src.services.cortador_ffmpeg import FastStreamCopyCutter

# =============================================================================
# ESTRUTURA UNIFICADA DE CAMINHOS DA FASE 2
# =============================================================================
PASTA_FASE2 = BASE_DIR / "data" / "fase2_mineracao"
PASTA_INSIGHTS_JSON = PASTA_FASE2 / "insights_json"

# Aprovados
PASTA_APROVADOS_SHORTS_AUDIOS = PASTA_FASE2 / "aprovados" / "shorts_9_16" / "audios"
PASTA_APROVADOS_SHORTS_TXT = PASTA_FASE2 / "aprovados" / "shorts_9_16" / "transcricoes"
PASTA_APROVADOS_SHORTS_JSON = PASTA_FASE2 / "aprovados" / "shorts_9_16" / "json"

PASTA_APROVADOS_MEDIOS_AUDIOS = PASTA_FASE2 / "aprovados" / "medios_16_9" / "audios"
PASTA_APROVADOS_MEDIOS_TXT = PASTA_FASE2 / "aprovados" / "medios_16_9" / "transcricoes"
PASTA_APROVADOS_MEDIOS_JSON = PASTA_FASE2 / "aprovados" / "medios_16_9" / "json"

# Rejeitados
PASTA_REJEITADOS_SHORTS_AUDIOS = PASTA_FASE2 / "rejeitados" / "shorts_9_16" / "audios"
PASTA_REJEITADOS_SHORTS_TXT = PASTA_FASE2 / "rejeitados" / "shorts_9_16" / "transcricoes"
PASTA_REJEITADOS_SHORTS_JSON = PASTA_FASE2 / "rejeitados" / "shorts_9_16" / "json"

PASTA_REJEITADOS_MEDIOS_AUDIOS = PASTA_FASE2 / "rejeitados" / "medios_16_9" / "audios"
PASTA_REJEITADOS_MEDIOS_TXT = PASTA_FASE2 / "rejeitados" / "medios_16_9" / "transcricoes"
PASTA_REJEITADOS_MEDIOS_JSON = PASTA_FASE2 / "rejeitados" / "medios_16_9" / "json"

PASTA_TEMP_SCRATCH = PASTA_FASE2 / "temp_scratch"

DESKTOP_DATASET_ROOT = Path(r"C:\Users\matheus\Desktop\dataset")
PASTAS_AUDIO_FALLBACK = [
    DESKTOP_DATASET_ROOT / "2026" / "audios",
    DESKTOP_DATASET_ROOT / "2025" / "audios",
    DESKTOP_DATASET_ROOT / "2024" / "audios",
    DESKTOP_DATASET_ROOT / "2023" / "audios",
    DESKTOP_DATASET_ROOT / "2022" / "audios",
    DESKTOP_DATASET_ROOT / "audios",
    BASE_DIR / "dataset" / "audios",
    BASE_DIR / "data" / "acervo_completo",
    BASE_DIR / "data" / "audios",
    BASE_DIR / "data" / "fase1_mapeamento" / "audios",
    BASE_DIR / "data" / "audio_podcasts",
    BASE_DIR / "dataset_transcricoes" / "audios",
]


def garantir_dependencias():
    """Verifica e instala dependências ausentes (ffmpeg-python, librosa, spacy, modelo pt_core_news_lg/sm)."""
    modulos_necessarios = {
        "ffmpeg": "ffmpeg-python",
        "librosa": "librosa",
        "spacy": "spacy",
        "numpy": "numpy"
    }

    for mod, pkg in modulos_necessarios.items():
        try:
            __import__(mod)
        except ImportError:
            print(f"📦 Instalando biblioteca ausente '{pkg}'...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", pkg])

    import spacy
    model_carregado = False
    for m in ["pt_core_news_sm", "pt_core_news_md", "pt_core_news_lg"]:
        try:
            spacy.load(m, disable=["ner"])
            model_carregado = True
            break
        except Exception:
            pass

    if not model_carregado:
        print("📦 Baixando modelo spaCy 'pt_core_news_sm' para Português...")
        try:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "pt_core_news_sm"])
        except Exception:
            subprocess.check_call([sys.executable, "-m", "spacy", "download", "pt_core_news_lg"])


# =============================================================================
# 1. FATIAMENTO I/O (ffmpeg-python com Seek & Margem de 0.3s)
# =============================================================================

class AudioSlicerIO:
    """Fatiador de precisão com busca Seek e respiro temporal de 0.3s."""

    def __init__(self, input_filepath: str, sample_rate: int = 44100):
        self.input_file = input_filepath
        self.sample_rate = sample_rate

        if not Path(self.input_file).is_file():
            raise FileNotFoundError(f"Falha de I/O: O áudio {self.input_file} não existe.")

    def slice_and_export(self, start_sec: float, end_sec: float, output_filepath: str) -> bool:
        import ffmpeg

        try:
            start_padded = max(0.0, start_sec - 0.3)
            end_padded = end_sec + 0.3

            (
                ffmpeg
                .input(self.input_file, ss=start_padded, to=end_padded)
                .output(
                    output_filepath,
                    acodec='libmp3lame',
                    audio_bitrate='192k',
                    ar=self.sample_rate,
                    loglevel='error'
                )
                .overwrite_output()
                .run(capture_stdout=True, capture_stderr=True)
            )
            return True
        except ffmpeg.Error as error_stream:
            detailed_error = error_stream.stderr.decode('utf8', errors='replace') if error_stream.stderr else str(error_stream)
            print(f"[Engine I/O] Erro FFmpeg: {detailed_error}")
            return False
        except Exception as ex:
            print(f"[Engine I/O] Erro ao fatiar áudio {self.input_file}: {ex}")
            return False


# =============================================================================
# 2. ANÁLISE DSP (librosa)
# =============================================================================

class DSPAnalyzer:
    """Motor DSP para inspeção de clipping e silêncio RMS."""

    def __init__(self, audio_filepath: str):
        import librosa
        self.y, self.sr = librosa.load(audio_filepath, sr=None)

    def detect_clipping_ratio(self, threshold: float = 0.995) -> float:
        import numpy as np
        if len(self.y) == 0:
            return 0.0
        abs_y = np.abs(self.y)
        clipped_samples = np.sum(abs_y >= threshold)
        return float(clipped_samples / len(self.y))

    def calculate_silence_ratio(self, db_threshold: float = -40.0, hop_length: int = 512) -> float:
        import librosa
        import numpy as np
        if len(self.y) == 0:
            return 1.0
        rms = librosa.feature.rms(y=self.y, hop_length=hop_length)[0]
        db_levels = librosa.amplitude_to_db(rms, ref=1.0)
        total_frames = len(db_levels)
        if total_frames == 0:
            return 1.0
        silent_frames = np.sum(db_levels < db_threshold)
        return float(silent_frames / total_frames)


# =============================================================================
# 3. ANÁLISE NLP (spaCy pt_core_news)
# =============================================================================

class TextCohesionNLP:
    """Inspeciona integridade sintática e WPM."""

    def __init__(self, spacy_model: str = "pt_core_news_sm", nlp_instance: Any = None):
        import spacy
        if nlp_instance is not None:
            self.nlp = nlp_instance
        else:
            for m in [spacy_model, "pt_core_news_sm", "pt_core_news_md", "pt_core_news_lg"]:
                try:
                    self.nlp = spacy.load(m, disable=["ner"])
                    break
                except Exception:
                    pass

    def analyze_sentence_completeness(self, text: str) -> Dict[str, Any]:
        if not text or not text.strip():
            return {"completeness": 0.0, "last_pos": "", "diagnostico": "Texto vazio."}

        doc = self.nlp(text)
        sentences = list(doc.sents)
        if not sentences:
            return {"completeness": 0.0, "last_pos": "", "diagnostico": "Sem oração detectada."}

        last_sentence = sentences[-1]
        tokens = list(last_sentence)
        if not tokens:
            return {"completeness": 0.0, "last_pos": "", "diagnostico": "Sem tokens na oração."}

        score = 1.0
        diagnosticos = []

        valid_terminals = {".", "!", "?", "...", "…”", "…", "''", '""', '"'}
        last_token_str = tokens[-1].text.strip()
        has_punctuation = any(last_token_str.endswith(p) for p in valid_terminals)
        if not has_punctuation:
            score -= 0.3
            diagnosticos.append("Ausência de pontuação terminal natural.")

        bad_tail_pos = {"ADP", "DET", "CCONJ", "SCONJ"}
        last_pos = tokens[-1].pos_
        if last_pos in bad_tail_pos:
            score -= 0.6
            diagnosticos.append(f"Decapitação pós-preposicional/conectivo ({last_pos}).")

        roots = [token for token in last_sentence if token.dep_ == "ROOT"]
        if not roots:
            score -= 0.3
            diagnosticos.append("Ausência de oração principal (ROOT).")

        diagnostico_final = "Sintaxe e coesão oracional íntegras." if not diagnosticos else " ".join(diagnosticos)

        return {
            "completeness": float(max(0.0, score)),
            "last_pos": last_pos,
            "diagnostico": diagnostico_final
        }

    def calculate_wpm(self, text: str, audio_duration_sec: float) -> float:
        if audio_duration_sec <= 0:
            return 0.0
        doc = self.nlp(text)
        words = [token for token in doc if token.is_alpha or token.is_digit]
        return float((len(words) / audio_duration_sec) * 60.0)


# =============================================================================
# 4. SCORING HEURÍSTICO
# =============================================================================

class HeuristicScorer:
    """Calcula pontuação unificada de 0 a 100 com veredito APROVADO / REJEITADO."""

    def compute_score(
        self,
        clip_ratio: float,
        sil_ratio: float,
        completeness: float,
        wpm: float,
        last_pos: str = ""
    ) -> Dict[str, Any]:
        clip_percent = clip_ratio * 100.0
        p_clip = min(60.0, ((clip_percent / 0.5) ** 2) * 10.0) if clip_percent > 0 else 0.0
        p_sil = max(0.0, (sil_ratio - 0.15) * 100.0)
        p_sin = (1.0 - completeness) * 35.0
        delta_wpm = abs(wpm - 145.0)
        p_wpm = max(0.0, (delta_wpm - 20.0) * 0.5)

        final_score = max(0.0, min(100.0, 100.0 - (p_clip + p_sil + p_sin + p_wpm)))

        if last_pos in {"ADP", "DET", "CCONJ", "SCONJ"} and final_score >= 70.0:
            final_score = 69.0

        status = "APROVADO" if final_score >= 70.0 else "REJEITADO"

        return {
            "final_score": round(final_score, 1),
            "status": status,
            "penalties": {
                "clipping": round(p_clip, 2),
                "silence": round(p_sil, 2),
                "syntax": round(p_sin, 2),
                "wpm": round(p_wpm, 2)
            }
        }


# =============================================================================
# 5. AUXILIARES E WORKER PARALELO DE QA
# =============================================================================

GLOBAL_NLP_INSTANCE = None


def init_worker():
    """Inicializa spaCy em cada worker paralelo."""
    global GLOBAL_NLP_INSTANCE
    import spacy
    for model_name in ["pt_core_news_sm", "pt_core_news_md", "pt_core_news_lg"]:
        try:
            GLOBAL_NLP_INSTANCE = spacy.load(model_name, disable=["ner"])
            break
        except Exception:
            pass


def formatar_timestamp(segundos: float) -> str:
    hrs = int(segundos // 3600)
    mins = int((segundos % 3600) // 60)
    secs = segundos % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def localizar_audio_origem(sermon_id: str) -> Optional[Path]:
    extensoes = [".mp4", ".mp3", ".webm", ".m4a", ".wav", ".opus", ".aac"]
    for pasta in PASTAS_AUDIO_FALLBACK:
        if not pasta.exists():
            continue
        for ext in extensoes:
            candidato = pasta / f"{sermon_id}{ext}"
            if candidato.is_file():
                return candidato

    id_yt = sermon_id.split("_")[1] if "_" in sermon_id else sermon_id
    for pasta in PASTAS_AUDIO_FALLBACK:
        if not pasta.exists():
            continue
        for arq in pasta.glob("*.*"):
            if arq.is_file() and (sermon_id in arq.name or id_yt in arq.name):
                return arq

    return None


def localizar_insight_corte(sermon_id: str, start_sec: float, end_sec: float) -> Optional[Dict[str, Any]]:
    if not PASTA_INSIGHTS_JSON.exists():
        return None

    json_data = None
    arq_exato = PASTA_INSIGHTS_JSON / f"{sermon_id}.insights.json"
    if arq_exato.is_file():
        try:
            with open(arq_exato, "r", encoding="utf-8") as f:
                json_data = json.load(f)
        except Exception:
            pass

    if not json_data:
        id_yt = sermon_id.split("_")[1] if "_" in sermon_id else sermon_id
        for arq in PASTA_INSIGHTS_JSON.glob("*.insights.json"):
            if sermon_id in arq.name or id_yt in arq.name:
                try:
                    with open(arq, "r", encoding="utf-8") as f:
                        json_data = json.load(f)
                        break
                except Exception:
                    pass

    if not json_data:
        return None

    cortes = json_data.get("short_form_cuts", []) + json_data.get("mid_form_cuts", [])
    for c in cortes:
        c_start = float(c.get("start_sec", -1))
        c_end = float(c.get("end_sec", -1))
        if abs(c_start - start_sec) < 1.5 and abs(c_end - end_sec) < 1.5:
            return c

    return None


def exportar_relatorio_txt(
    caminho_txt: Path,
    nome_audio: str,
    start_sec: float,
    end_sec: float,
    score_data: Dict[str, Any],
    clip_ratio: float,
    sil_ratio: float,
    wpm: float,
    nlp_completeness: float,
    diagnostico_nlp: str,
    texto_trecho: str,
    insight_corte: Optional[Dict[str, Any]] = None
):
    start_fmt = formatar_timestamp(start_sec)
    end_fmt = formatar_timestamp(end_sec)
    score = score_data["final_score"]
    status = score_data["status"]
    penalties = score_data["penalties"]

    bloco_insight = ""
    if insight_corte:
        hook_a = insight_corte.get("title_hook_a", "N/A")
        hook_b = insight_corte.get("title_hook_b", "N/A")
        theological = insight_corte.get("theological_analysis", {})
        prof = theological.get("sermon_profile", "Exortação")

        bloco_insight = f"""
[INSIGHTS DE MINERAÇÃO DA FASE 2]
  • Título / Hook Principal: {hook_a}
  • Título Curiosidade (Hook B): {hook_b}
  • Perfil Teológico: {prof}
"""

    conteudo = f"""========================================================================
==================== RELATÓRIO DE QA HEURÍSTICO - FASE 2 UNIFICADA
Artefacto Físico: {nome_audio}
Indexador Temporal: {start_fmt} -> {end_fmt}
Veredito da Camada QA: [{status}] Índice de Triagem (Score): {score:.1f} / 100
{bloco_insight}
[AVALIAÇÃO ACÚSTICA DSP]
  • Ceifamento de Sinal (Clipping): {clip_ratio * 100:.1f}% (Penalização: -{penalties['clipping']:.1f} pts)
  • Silêncio Inativo RMS: {sil_ratio * 100:.1f}% (Penalização: -{penalties['silence']:.1f} pts)

[AVALIAÇÃO SINTÁTICA NLP]
  • Cadência Nominal (WPM): {wpm:.1f} (Penalização: -{penalties['wpm']:.1f} pts)
  • Integridade Coesiva: {nlp_completeness:.2f}/1.0 (Penalização: -{penalties['syntax']:.1f} pts)
    Diagnóstico: {diagnostico_nlp}

[TRANSCRIPTO SINTÉTICO BASE]
"{texto_trecho}"
========================================================================
"""
    with open(caminho_txt, "w", encoding="utf-8") as f:
        f.write(conteudo)


def processar_corte_worker(item_task: Tuple[int, Dict[str, str]]) -> Dict[str, Any]:
    global GLOBAL_NLP_INSTANCE
    idx, row = item_task

    sermon_id = row.get("sermon_id") or row.get("\ufeffsermon_id", f"corte_{idx}")
    start_sec = float(row.get("start_sec", 0.0))
    end_sec = float(row.get("end_sec", 0.0))
    duracao = float(row.get("duracao") or row.get("duration") or (end_sec - start_sec))
    texto_trecho = str(row.get("texto_trecho") or row.get("text_snippet") or row.get("text") or "").strip()

    prefixo = f"corte_{idx:03d}_{sermon_id[:35]}"
    PASTA_TEMP_SCRATCH.mkdir(parents=True, exist_ok=True)
    caminho_mp3_temp = PASTA_TEMP_SCRATCH / f"temp_{idx:03d}_{sermon_id[:20]}.mp3"

    audio_origem = localizar_audio_origem(sermon_id)
    if not audio_origem:
        return {"idx": idx, "sermon_id": sermon_id, "status": "ERRO_AUDIO_NAO_ENCONTRADO", "score": 0.0}

    try:
        slicer = AudioSlicerIO(str(audio_origem), sample_rate=44100)
        ok_slice = slicer.slice_and_export(start_sec, end_sec, str(caminho_mp3_temp))
        if not ok_slice or not caminho_mp3_temp.exists():
            return {"idx": idx, "sermon_id": sermon_id, "status": "ERRO_FFMPEG_SLICE", "score": 0.0}

        dsp = DSPAnalyzer(str(caminho_mp3_temp))
        clip_ratio = dsp.detect_clipping_ratio(threshold=0.995)
        sil_ratio = dsp.calculate_silence_ratio(db_threshold=-40.0, hop_length=512)

        nlp_engine = TextCohesionNLP(nlp_instance=GLOBAL_NLP_INSTANCE)
        nlp_info = nlp_engine.analyze_sentence_completeness(texto_trecho)
        wpm = nlp_engine.calculate_wpm(texto_trecho, audio_duration_sec=duracao)

        scorer = HeuristicScorer()
        score_data = scorer.compute_score(
            clip_ratio=clip_ratio,
            sil_ratio=sil_ratio,
            completeness=nlp_info["completeness"],
            wpm=wpm,
            last_pos=nlp_info["last_pos"]
        )

        tipo_corte = str(row.get("tipo", ""))
        is_short = "Short" in tipo_corte or duracao <= 120.0

        if score_data["status"] == "APROVADO":
            if is_short:
                pasta_audio_dest = PASTA_APROVADOS_SHORTS_AUDIOS
                pasta_txt_dest = PASTA_APROVADOS_SHORTS_TXT
                pasta_json_dest = PASTA_APROVADOS_SHORTS_JSON
            else:
                pasta_audio_dest = PASTA_APROVADOS_MEDIOS_AUDIOS
                pasta_txt_dest = PASTA_APROVADOS_MEDIOS_TXT
                pasta_json_dest = PASTA_APROVADOS_MEDIOS_JSON
        else:
            if is_short:
                pasta_audio_dest = PASTA_REJEITADOS_SHORTS_AUDIOS
                pasta_txt_dest = PASTA_REJEITADOS_SHORTS_TXT
                pasta_json_dest = PASTA_REJEITADOS_SHORTS_JSON
            else:
                pasta_audio_dest = PASTA_REJEITADOS_MEDIOS_AUDIOS
                pasta_txt_dest = PASTA_REJEITADOS_MEDIOS_TXT
                pasta_json_dest = PASTA_REJEITADOS_MEDIOS_JSON

        caminho_mp3_final = pasta_audio_dest / f"{prefixo}.mp3"
        caminho_txt_final = pasta_txt_dest / f"{prefixo}.txt"
        caminho_json_final = pasta_json_dest / f"{prefixo}.json"

        if caminho_mp3_final.exists():
            caminho_mp3_final.unlink()
        shutil.move(str(caminho_mp3_temp), str(caminho_mp3_final))

        insight_corte = localizar_insight_corte(sermon_id, start_sec, end_sec)

        exportar_relatorio_txt(
            caminho_txt=caminho_txt_final,
            nome_audio=caminho_mp3_final.name,
            start_sec=start_sec,
            end_sec=end_sec,
            score_data=score_data,
            clip_ratio=clip_ratio,
            sil_ratio=sil_ratio,
            wpm=wpm,
            nlp_completeness=nlp_info["completeness"],
            diagnostico_nlp=nlp_info["diagnostico"],
            texto_trecho=texto_trecho,
            insight_corte=insight_corte
        )

        payload_json = {
            "idx": idx,
            "sermon_id": sermon_id,
            "prefixo": prefixo,
            "start_sec": start_sec,
            "end_sec": end_sec,
            "duracao": duracao,
            "qa_metrics": {
                "status": score_data["status"],
                "score": score_data["final_score"],
                "clipping_pct": round(clip_ratio * 100.0, 2),
                "silence_pct": round(sil_ratio * 100.0, 2),
                "wpm": round(wpm, 1),
                "nlp_completeness": round(nlp_info["completeness"], 2),
                "diagnostico_nlp": nlp_info["diagnostico"]
            },
            "fase2_insights": insight_corte or {}
        }
        with open(caminho_json_final, "w", encoding="utf-8") as f:
            json.dump(payload_json, f, ensure_ascii=False, indent=2)

        return {
            "idx": idx,
            "sermon_id": sermon_id,
            "status": score_data["status"],
            "score": score_data["final_score"],
            "wpm": wpm,
            "clipping_pct": clip_ratio * 100.0,
            "silence_pct": sil_ratio * 100.0,
            "mp3_path": str(caminho_mp3_final),
            "txt_path": str(caminho_txt_final)
        }

    except Exception as ex:
        if caminho_mp3_temp.exists():
            try:
                caminho_mp3_temp.unlink()
            except Exception:
                pass
        return {"idx": idx, "sermon_id": sermon_id, "status": "ERRO_PROCESSAMENTO", "score": 0.0}


# =============================================================================
# 6. PAINEL DE CONTROLE TERMINAL
# =============================================================================

class Fase2TerminalPainel:
    """Painel de Terminal limpo para acompanhar Mineração + Triagem QA."""

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
            header_text.append("🏛️  IBPM CR AUTOMATION SYSTEM — FASE 2 UNIFICADA (MINERAÇÃO + TRIAGEM QA)\n", style="bold yellow")
            header_text.append(f"• Cultos Alvo    : {self.total_cultos} transcrição(ões)\n", style="bold white")
            header_text.append("• Mineração NLP  : TextRank + NMS + Filtro Estrito Pregação vs Louvor/Oração\n", style="bold green")
            header_text.append("• Triagem QA AQC : Seek FFmpeg (+0.3s padding) + DSP librosa + spaCy Syntactic Parser", style="dim white")
            self.console.print(Panel(header_text, border_style="yellow", expand=False))
            self.console.print("[dim cyan]──────── Minando Transcrições e Processando Mídias ────────[/dim cyan]\n")

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
            self.console.print(Panel(t, title="[bold bright_green] 🎉 RESUMO MINERAÇÃO FASE 2 UNIFICADA [/bold bright_green]", border_style="green", expand=False))


# =============================================================================
# 7. ORQUESTRADOR PRINCIPAL PIPELINE FASE 2
# =============================================================================

class PipelineMineracaoFase2:
    """Pipeline Unificado da Fase 2: Mineração Semântica + Triagem QA + Fatiamento Físico de Áudios."""

    EXTENSOES_MIDIA = {".webm", ".mp4", ".mkv", ".mp3", ".wav", ".m4a"}

    def __init__(self, output_dir: Optional[Path] = None, filtro: Optional[str] = None, limit: Optional[int] = None, usar_painel: bool = True):
        self.logger = get_logger("PipelineFase2MineracaoUnificada")
        self.miner = DualSermonMiner()
        self.cutter = FastStreamCopyCutter()
        self.filtro = filtro
        self.limit = limit
        self.usar_painel = usar_painel

        self.pasta_base = Path(output_dir).resolve() if output_dir else PASTA_FASE2
        self.dir_insights = self.pasta_base / "insights_json"
        self.arq_csv = self.pasta_base / "relatorio_cortes.csv"
        self.arq_playlists = self.pasta_base / "playlists_tematicas.json"

        DESKTOP_DATASET = Path(r"C:\Users\matheus\Desktop\dataset")
        audios_desktop = [DESKTOP_DATASET / ano / "audios" for ano in ["2026", "2025", "2024", "2023", "2022"]] + [DESKTOP_DATASET / "audios"]
        trans_desktop_json = [DESKTOP_DATASET / ano / "transcriptions" / "json" for ano in ["2026", "2025", "2024", "2023", "2022"]] + [DESKTOP_DATASET / "transcriptions" / "json"]
        trans_desktop_txt = [DESKTOP_DATASET / ano / "transcriptions" / "txt" for ano in ["2026", "2025", "2024", "2023", "2022"]] + [DESKTOP_DATASET / "transcriptions" / "txt"]

        self.dir_audios_candidatos = audios_desktop + PASTAS_AUDIO_FALLBACK
        self.dir_transcricoes_candidatos = trans_desktop_json + trans_desktop_txt + [
            BASE_DIR / "dataset" / "transcriptions" / "json",
            BASE_DIR / "dataset" / "transcriptions" / "txt",
            BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes" / "txt",
            BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes" / "json",
            BASE_DIR / "data" / "transcriptions" / "txt",
            BASE_DIR / "data" / "transcriptions" / "json",
            BASE_DIR / "data" / "1.TRANSCRICOES",
        ]

        self.todos_cortes_csv: List[dict] = []
        self.cortes_medios_playlists: List[dict] = []

    def preparar_diretorios(self):
        for d in [
            self.pasta_base, self.dir_insights,
            PASTA_APROVADOS_SHORTS_AUDIOS, PASTA_APROVADOS_SHORTS_TXT, PASTA_APROVADOS_SHORTS_JSON,
            PASTA_APROVADOS_MEDIOS_AUDIOS, PASTA_APROVADOS_MEDIOS_TXT, PASTA_APROVADOS_MEDIOS_JSON,
            PASTA_REJEITADOS_SHORTS_AUDIOS, PASTA_REJEITADOS_SHORTS_TXT, PASTA_REJEITADOS_SHORTS_JSON,
            PASTA_REJEITADOS_MEDIOS_AUDIOS, PASTA_REJEITADOS_MEDIOS_TXT, PASTA_REJEITADOS_MEDIOS_JSON
        ]:
            d.mkdir(parents=True, exist_ok=True)

    def extrair_yt_id(self, nome_arquivo: str) -> str:
        stem = Path(nome_arquivo).stem
        m_prefix = re.search(r"^\d{3}_([a-zA-Z0-9_-]{11})_", stem)
        if m_prefix:
            return m_prefix.group(1)
        m_any = re.search(r"_([a-zA-Z0-9_-]{11})_", stem)
        if m_any:
            return m_any.group(1)
        m_fallback = re.search(r"([a-zA-Z0-9_-]{11})", stem)
        return m_fallback.group(1) if m_fallback else stem

    def extrair_indice(self, nome_arquivo: str) -> Optional[str]:
        m = re.match(r"^(\d{3})_", Path(nome_arquivo).name)
        return m.group(1) if m else None

    def mapear_acervo(self) -> Tuple[Dict[str, Path], Dict[str, Path]]:
        mapa_transcricoes_bruto = {}
        mapa_midias_bruto = {}
        mapa_midias_por_indice = {}
        nomes_originais = {}

        for dir_audio in self.dir_audios_candidatos:
            if dir_audio.exists():
                for arq in dir_audio.iterdir():
                    if arq.is_file() and arq.suffix.lower() in self.EXTENSOES_MIDIA:
                        yt_id = self.extrair_yt_id(arq.name)
                        idx = self.extrair_indice(arq.name)
                        if yt_id not in mapa_midias_bruto:
                            mapa_midias_bruto[yt_id] = arq
                            nomes_originais[yt_id] = arq.stem
                        if idx and idx not in mapa_midias_por_indice:
                            mapa_midias_por_indice[idx] = arq

        formatos_texto = {".txt", ".srt", ".vtt"}
        for dir_trans in self.dir_transcricoes_candidatos:
            if dir_trans.exists():
                for arq in dir_trans.iterdir():
                    if arq.is_file():
                        ext = arq.suffix.lower()
                        yt_id = self.extrair_yt_id(arq.name)
                        idx = self.extrair_indice(arq.name)
                        chave = idx if idx else yt_id
                        if ext in formatos_texto and chave not in mapa_transcricoes_bruto:
                            mapa_transcricoes_bruto[chave] = (yt_id, idx, arq)
                        elif ext == ".json" and not arq.name.endswith(".insights.json") and chave not in mapa_transcricoes_bruto:
                            mapa_transcricoes_bruto[chave] = (yt_id, idx, arq)

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

        mapa_final_transcricoes = {}
        mapa_final_midias = {}
        for chave, (yt_id, idx, arq_trans) in mapa_transcricoes_bruto.items():
            if yt_id in desqualificados_ids:
                continue

            arq_midia = mapa_midias_bruto.get(yt_id)
            if not arq_midia and idx:
                arq_midia = mapa_midias_por_indice.get(idx)

            sermon_id = arq_midia.stem if arq_midia else arq_trans.stem
            mapa_final_transcricoes[sermon_id] = arq_trans
            if arq_midia:
                mapa_final_midias[sermon_id] = arq_midia

        # Ordenar do culto mais recente (457) para o mais antigo (001)
        def _chave_ordenacao_reversa(k):
            m = re.match(r'^(\d+)', k)
            return int(m.group(1)) if m else -1

        chaves_ordenadas = sorted(mapa_final_transcricoes.keys(), key=_chave_ordenacao_reversa, reverse=True)
        mapa_final_transcricoes = {k: mapa_final_transcricoes[k] for k in chaves_ordenadas}

        return mapa_final_transcricoes, mapa_final_midias

    def carregar_transcricao(self, caminho: Path) -> Tuple[str, List[dict]]:
        ext = caminho.suffix.lower()
        try:
            if ext == ".json":
                with open(caminho, "r", encoding="utf-8") as f:
                    dados = json.load(f)
                texto = ""
                segmentos = []
                if isinstance(dados, dict):
                    texto = dados.get("text", "") or dados.get("texto", "")
                    segmentos = dados.get("segments", []) or dados.get("segmentos", [])
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

        if self.limit and self.limit > 0:
            chaves_limitadas = list(mapa_trans.keys())[:self.limit]
            mapa_trans = {k: mapa_trans[k] for k in chaves_limitadas}
            mapa_midias = {k: v for k, v in mapa_midias.items() if k in mapa_trans}

        if not mapa_trans:
            print("⚠️ Nenhuma transcrição encontrada com os filtros atuais. Encerrando.")
            return

        total_cultos = len(mapa_trans)
        painel = Fase2TerminalPainel(total_cultos=total_cultos, usar_painel=self.usar_painel)
        painel.start()

        try:
            for idx, (sermon_id, caminho_arq) in enumerate(mapa_trans.items(), 1):
                texto, segmentos = self.carregar_transcricao(caminho_arq)
                duracao_estimada = 0.0
                if segmentos and isinstance(segmentos, list):
                    duracao_estimada = float(segmentos[-1].get("end", 0.0)) if isinstance(segmentos[-1], dict) else 0.0

                if not texto or len(texto) < 200 or (duracao_estimada > 0 and duracao_estimada < 300.0):
                    painel.registrar_culto(sermon_id, 0, 0, 0.0, status="CURTO")
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
        self.executar_triagem_qa()

    def _gerar_artefatos(self, sucessos: int, total: int):
        print("\n" + "─" * 75)
        if self.todos_cortes_csv:
            campos = ["sermon_id", "tipo", "start_sec", "end_sec", "duracao", "score", "titulo", "texto_trecho"]
            with open(self.arq_csv, "w", encoding="utf-8-sig", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=campos)
                writer.writeheader()
                for c in self.todos_cortes_csv:
                    st = float(c.get("start_sec", c.get("start", 0)))
                    et = float(c.get("end_sec", c.get("end", 0)))
                    writer.writerow({
                        "sermon_id": c.get("sermon_id", ""),
                        "tipo": c.get("tipo", ""),
                        "start_sec": round(st, 2),
                        "end_sec": round(et, 2),
                        "duracao": round(et - st, 2),
                        "score": round(float(c.get("score", 0)), 3),
                        "titulo": c.get("title_hook_a", c.get("titulo", "Corte Automático")),
                        "texto_trecho": c.get("text_snippet", c.get("text", "")).replace("\n", " ")
                    })
            print(f"📊 Relatório CSV exportado: '{self.arq_csv}' ({len(self.todos_cortes_csv)} cortes).")

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

    def executar_triagem_qa(self):
        """Etapa Integrada de Triagem QA Automática & Fatiamento Físico de Áudios."""
        garantir_dependencias()
        print("\n==========================================================================")
        print("🔊 FASE 2 UNIFICADA — TRIAGEM QA AUTOMÁTICA & FATIAMENTO DE ÁUDIO")
        print("==========================================================================")

        if not self.todos_cortes_csv and self.arq_csv.exists():
            with open(self.arq_csv, "r", encoding="utf-8-sig") as f:
                self.todos_cortes_csv = list(csv.DictReader(f))

        total_cortes = len(self.todos_cortes_csv)
        if total_cortes == 0:
            print("⚠️ Nenhum corte disponível para triagem QA.")
            return

        tasks = [(idx, row) for idx, row in enumerate(self.todos_cortes_csv, start=1)]
        num_cpus = max(1, min(os.cpu_count() or 2, 2))
        print(f"🚀 Processando Triagem QA em paralelo ({num_cpus} workers)...\n")

        aprovados = 0
        rejeitados = 0
        erros = 0
        start_t = time.time()

        with ProcessPoolExecutor(max_workers=num_cpus, initializer=init_worker) as executor:
            futures = {executor.submit(processar_corte_worker, task): task for task in tasks}
            for future in as_completed(futures):
                res = future.result()
                st = res.get("status")
                sc = res.get("score", 0.0)
                idx = res.get("idx")
                sid = res.get("sermon_id", "")[:30]

                if st == "APROVADO":
                    aprovados += 1
                    badge = "✅ [APROVADO]"
                elif st == "REJEITADO":
                    rejeitados += 1
                    badge = "⚠️ [REJEITADO]"
                else:
                    erros += 1
                    badge = f"❌ [{st}]"

                wpm_val = res.get("wpm", 0.0)
                clip_val = res.get("clipping_pct", 0.0)
                sil_val = res.get("silence_pct", 0.0)

                print(f"[{idx:03d}/{total_cortes:03d}] {badge:<14} | Score: {sc:5.1f} | WPM: {wpm_val:5.1f} | Clip: {clip_val:4.1f}% | Sil: {sil_val:4.1f}% | {sid}")

        elapsed = time.time() - start_t
        elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

        print("\n==========================================================================")
        print("🎉 FASE 2 UNIFICADA FINALIZADA COM SUCESSO")
        print(f"   • Tempo da Triagem : {elapsed_str}")
        print(f"   • Cortes Analisados : {total_cortes}")
        pasta_aprovados = PASTA_FASE2 / "aprovados"
        pasta_rejeitados = PASTA_FASE2 / "rejeitados"
        print(f"   • APROVADOS        : {aprovados} ({aprovados/total_cortes*100:.1f}%) -> {pasta_aprovados.resolve()}")
        print(f"   • REJEITADOS       : {rejeitados} ({rejeitados/total_cortes*100:.1f}%) -> {pasta_rejeitados.resolve()}")
        print(f"   • Erros / Falhas   : {erros}")
        print("==========================================================================\n")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Pipeline Fase 2 Unificada (Mineração + QA)")
    parser.add_argument("--filtro", "--arquivo", type=str, default=None, help="Filtra transcrição por ID ou nome")
    parser.add_argument("--limit", type=int, default=None, help="Limita a quantidade de cultos a processar (ex: --limit 3)")
    parser.add_argument("--output-dir", type=str, default=None, help="Diretório customizado de saída")
    parser.add_argument("--no-painel", action="store_true", help="Desativa o painel Rich no terminal")
    args = parser.parse_args()

    pipeline = PipelineMineracaoFase2(
        output_dir=args.output_dir,
        filtro=args.filtro,
        limit=args.limit,
        usar_painel=not args.no_painel
    )
    pipeline.executar()
