#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FASE 2.5 — TRIAGEM E FILTRO DE QUALITY ASSURANCE (QA) COM GERADOR DE AMOSTRAS LOCAIS
IBPM CR AUTOMATION SYSTEM — Arquitetura Orientada a Objetos (DSP + NLP + Heurística Multidimensional)

Descrição:
  Este script atua como Filtro de QA Automático (AQC) e Gerador de Amostras de Cortes Locais.
  - Ingestão: `data/fase2_mineracao/relatorio_cortes.csv` e `data/acervo_completo/` (com fallbacks locais)
  - Fatiamento I/O: ffmpeg-python com busca temporal indexada (input seek) e re-codificação mp3 libmp3lame 192k
  - Análise DSP: librosa (Clipping Ratio + RMS Silence Ratio em dB)
  - Análise NLP: spaCy `pt_core_news_lg` (disable=["ner"]) para integridade sintática e WPM
  - Scoring: Heurística multidimensional com veredito (Score >= 70 = APROVADO, senão REJEITADO)
  - Exportação: `data/fase2_5_revisao/` com pares `corte_XXX_id.mp3` e `corte_XXX_id.txt`
  - Concorrência: ProcessPoolExecutor com carregamento global do modelo spaCy no worker.
"""

import sys
import os
import json
import csv
import re
import time
import subprocess
import traceback
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
from concurrent.futures import ProcessPoolExecutor, as_completed

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
CSV_ENTRADA = BASE_DIR / "data" / "fase2_mineracao" / "relatorio_cortes.csv"
PASTA_ACERVO = BASE_DIR / "data" / "acervo_completo"
PASTA_SAIDA = BASE_DIR / "data" / "fase2_5_revisao"

# Diretorios alternativos de busca de audio (fallbacks)
PASTAS_AUDIO_FALLBACK = [
    BASE_DIR / "data" / "acervo_completo",
    BASE_DIR / "dataset_transcricoes" / "audios",
    BASE_DIR / "data" / "audio_podcasts",
    BASE_DIR / "data" / "fase1_mapeamento" / "transcricoes"
]


def garantir_dependencias():
    """Verifica e instala dependencias ausentes (ffmpeg-python, librosa, spacy, modelo pt_core_news_lg)."""
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

    # Verificar modelo spacy pt_core_news_lg
    try:
        # pyrefly: ignore [missing-import]
        import spacy
        spacy.load("pt_core_news_lg", disable=["ner"])
    except Exception:
        print("📦 Baixando modelo spaCy 'pt_core_news_lg' para idioma Português...")
        subprocess.check_call([sys.executable, "-m", "spacy", "download", "pt_core_news_lg"])


# =============================================================================
# 1. FATIAMENTO I/O (ffmpeg-python com Input Seek)
# =============================================================================

class AudioSlicerIO:
    """
    Abstração arquitetural de baixo nível para fatiamento de precisão de áudio
    utilizando instâncias subprocessadas do motor FFmpeg.
    """

    def __init__(self, input_filepath: str, sample_rate: int = 44100):
        self.input_file = input_filepath
        self.sample_rate = sample_rate

        if not Path(self.input_file).is_file():
            raise FileNotFoundError(f"Falha de I/O: O artefato de origem {self.input_file} não existe.")

    def slice_and_export(self, start_sec: float, end_sec: float, output_filepath: str) -> bool:
        """
        Executa uma busca temporal indexada (input seek) combinada com re-codificação,
        contornando anomalias associadas ao alinhamento de keyframes do parâmetro '-c copy'.
        """
        # pyrefly: ignore [missing-import]
        import ffmpeg

        try:
            # Definição topológica do grafo do FFmpeg com busca rápida ANTES do input (-ss / -to)
            (
                ffmpeg
                .input(self.input_file, ss=start_sec, to=end_sec)
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
            print(f"[Engine I/O] Discrepância detectada no multiplexador FFmpeg: {detailed_error}")
            return False
        except Exception as ex:
            print(f"[Engine I/O] Erro ao fatiar áudio {self.input_file}: {ex}")
            return False


# =============================================================================
# 2. MOTOR DSP (librosa - Clipping Ratio & Silence Ratio)
# =============================================================================

class DSPAnalyzer:
    """
    Motor algorítmico e heurístico focado no Processamento Digital de Sinais (DSP),
    projetado para orquestração de controle de qualidade audiovisual contínuo.
    """

    def __init__(self, audio_filepath: str):
        # pyrefly: ignore [missing-import]
        import librosa
        # O carregamento contorna o resampler interno (sr=None), mitigando custos de descompressão
        self.y, self.sr = librosa.load(audio_filepath, sr=None)

    def detect_clipping_ratio(self, threshold: float = 0.995) -> float:
        """
        Inspeciona a amplitude retificada para identificar agregados destrutivos (clipping).
        Retorna uma porcentagem representativa (0.0 a 1.0) da população de amostras danificadas.
        """
        import numpy as np

        if len(self.y) == 0:
            return 0.0

        abs_y = np.abs(self.y)
        clipped_samples = np.sum(abs_y >= threshold)
        clipping_ratio = clipped_samples / len(self.y)
        return float(clipping_ratio)

    def calculate_silence_ratio(self, db_threshold: float = -40.0, hop_length: int = 512) -> float:
        """
        Baseado na técnica de Raiz Quadrada Média (RMS).
        Estima a fração temporal em que a pressão sonora afunda abaixo do noise floor orgânico (-40 dB).
        """
        # pyrefly: ignore [missing-import]
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
        silence_ratio = silent_frames / total_frames
        return float(silence_ratio)


# =============================================================================
# 3. MOTOR NLP (spaCy pt_core_news_lg - Integridade Sintática e WPM)
# =============================================================================

class TextCohesionNLP:
    """
    Abstração avançada que consome vetores de linguagem e tabelas de
    árvores de dependência da língua Portuguesa via spaCy.
    """

    def __init__(self, spacy_model: str = "pt_core_news_lg", nlp_instance: Any = None):
        # pyrefly: ignore [missing-import]
        import spacy
        if nlp_instance is not None:
            self.nlp = nlp_instance
        else:
            self.nlp = spacy.load(spacy_model, disable=["ner"])

    def analyze_sentence_completeness(self, text: str) -> Dict[str, Any]:
        """
        Efetua inferência sobre a coesão semântica através do parser de dependência.
        Retorna pontuação de integridade (0.0 a 1.0), última tag POS e diagnóstico.
        """
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

        # Validação 1: Pontuação Terminal Natural
        valid_terminals = {".", "!", "?", "...", "…”", "…", "''", '""', '"'}
        last_token_str = tokens[-1].text.strip()
        has_punctuation = any(last_token_str.endswith(p) for p in valid_terminals)
        if not has_punctuation:
            score -= 0.3
            diagnosticos.append("Ausência de pontuação terminal natural.")

        # Validação 2: Anatomia Sintática Crítica (Decapitação pós-preposicional / conectivo)
        bad_tail_pos = {"ADP", "DET", "CCONJ", "SCONJ"}
        last_pos = tokens[-1].pos_
        if last_pos in bad_tail_pos:
            score -= 0.6
            diagnosticos.append(f"Decapitação pós-preposicional/conectivo. Estrutura suspensa na tag POS ({last_pos}).")

        # Validação 3: Ancoragem de Árvore (Raiz Oracional)
        roots = [token for token in last_sentence if token.dep_ == "ROOT"]
        if not roots:
            score -= 0.3
            diagnosticos.append("Ausência de oração principal (ROOT).")

        if not diagnosticos:
            diagnostico_final = "Sintaxe e coesão oracional íntegras."
        else:
            diagnostico_final = " ".join(diagnosticos)

        return {
            "completeness": float(max(0.0, score)),
            "last_pos": last_pos,
            "diagnostico": diagnostico_final
        }

    def calculate_wpm(self, text: str, audio_duration_sec: float) -> float:
        """
        Mede a cadência vocabular (Palavras Por Minuto) utilizando apenas lexemas alfa-numéricos.
        """
        if audio_duration_sec <= 0:
            return 0.0

        doc = self.nlp(text)
        words = [token for token in doc if token.is_alpha or token.is_digit]
        num_words = len(words)
        wpm = (num_words / audio_duration_sec) * 60.0
        return float(wpm)


# =============================================================================
# 4. MOTOR DE SCORING HEURÍSTICO MULTIDIMENSIONADO
# =============================================================================

class HeuristicScorer:
    """
    Agregador estatístico para fusão de métricas acústicas e semânticas.
    Processa equações polinomiais e lineares para definir vereditos de aprovação.
    """

    def compute_score(
        self,
        clip_ratio: float,
        sil_ratio: float,
        completeness: float,
        wpm: float,
        last_pos: str = ""
    ) -> Dict[str, Any]:
        """
        Calcula pontuação unificada (0 a 100) e penalidades aplicadas.
        Rejeita sumariamente se terminar em preposição/determinante (ADP/DET).
        """
        # 1. Penalidade de Ceifamento de Sinal (Clipping A/D - Exponencial Grau 2)
        clip_percent = clip_ratio * 100.0
        if clip_percent > 0:
            p_clip = min(60.0, ((clip_percent / 0.5) ** 2) * 10.0)
        else:
            p_clip = 0.0

        # 2. Penalidade por Ausência Energética / Silêncio Excessivo
        p_sil = max(0.0, (sil_ratio - 0.15) * 100.0)

        # 3. Penalidade por Rebatimento de Coesão Sintática NLP
        p_sin = (1.0 - completeness) * 35.0

        # 4. Avaliação de Pacing e Cadência Narrativa (WPM - Padrão 145 ±20 WPM)
        delta_wpm = abs(wpm - 145.0)
        p_wpm = max(0.0, (delta_wpm - 20.0) * 0.5)

        # Cálculo do Score Final
        final_score = 100.0 - (p_clip + p_sil + p_sin + p_wpm)
        final_score = max(0.0, min(100.0, final_score))

        # Rejeição estrita se terminar em preposição / determinante solto (ADP / DET)
        if last_pos in {"ADP", "DET", "CCONJ", "SCONJ"} and final_score >= 70.0:
            final_score = 69.0  # Força rebaixamento para REJEITADO

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
# 5. GERADOR DE ARTEFATOS (.TXT) E UTILS DE BUSCA DE ÁUDIO
# =============================================================================

def formatar_timestamp(segundos: float) -> str:
    """Converte segundos para formato HH:MM:SS.mmm."""
    hrs = int(segundos // 3600)
    mins = int((segundos % 3600) // 60)
    secs = segundos % 60
    return f"{hrs:02d}:{mins:02d}:{secs:06.3f}"


def localizar_audio_origem(sermon_id: str) -> Optional[Path]:
    """
    Busca o arquivo de áudio correspondente ao sermon_id no acervo completo
    e nas pastas alternativas de fallback.
    """
    extensoes = [".mp3", ".webm", ".m4a", ".wav", ".opus", ".aac"]

    # 1. Busca exata por nome de arquivo + extensão nas pastas
    for pasta in PASTAS_AUDIO_FALLBACK:
        if not pasta.exists():
            continue
        for ext in extensoes:
            candidato = pasta / f"{sermon_id}{ext}"
            if candidato.is_file():
                return candidato

    # 2. Busca por substring do sermon_id ou ID do YouTube
    id_yt = sermon_id.split("_")[1] if "_" in sermon_id else sermon_id
    for pasta in PASTAS_AUDIO_FALLBACK:
        if not pasta.exists():
            continue
        for arq in pasta.glob("*.*"):
            if arq.is_file() and (sermon_id in arq.name or id_yt in arq.name):
                return arq

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
    texto_trecho: str
):
    """
    Exporta o relatório individual de QA Heurístico formatado em UTF-8.
    """
    start_fmt = formatar_timestamp(start_sec)
    end_fmt = formatar_timestamp(end_sec)
    score = score_data["final_score"]
    status = score_data["status"]
    penalties = score_data["penalties"]

    conteudo = f"""========================================================================
==================== RELATÓRIO DE QA HEURÍSTICO - FASE 2.5
Artefacto Físico: {nome_audio}
Indexador Temporal: {start_fmt} -> {end_fmt}
Veredito da Camada QA: [{status}] Índice de Triagem (Score): {score:.1f} / 100

[AVALIAÇÃO ACÚSTICA DSP]
  • Degradação A/D (Clipping): {clip_ratio * 100:.1f}% (Penalização: -{penalties['clipping']:.1f} pts)
  • Volume Residual Inativo: {sil_ratio * 100:.1f}% (Penalização: -{penalties['silence']:.1f} pts)

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


# =============================================================================
# 6. WORKER PARALELO (ProcessPoolExecutor)
# =============================================================================

# Variável global para reter a instância pesada do spaCy por processo trabalhador
GLOBAL_NLP_INSTANCE = None


def init_worker():
    """Inicializador global executado na criação de cada worker do pool."""
    global GLOBAL_NLP_INSTANCE
    # pyrefly: ignore [missing-import]
    import spacy
    GLOBAL_NLP_INSTANCE = spacy.load("pt_core_news_lg", disable=["ner"])


def processar_corte_worker(item_task: Tuple[int, Dict[str, str]]) -> Dict[str, Any]:
    """
    Função executed no worker isolado para fatiamento, análise DSP, NLP e scoring.
    """
    global GLOBAL_NLP_INSTANCE
    idx, row = item_task

    sermon_id = row.get("sermon_id") or row.get("\ufeffsermon_id", f"corte_{idx}")
    start_sec = float(row.get("start_sec", 0.0))
    end_sec = float(row.get("end_sec", 0.0))
    duracao = end_sec - start_sec
    texto_trecho = row.get("texto_trecho", "").strip()

    # Nomes dos artefatos de saída
    prefixo = f"corte_{idx:03d}_{sermon_id[:35]}"
    caminho_mp3_saida = PASTA_SAIDA / f"{prefixo}.mp3"
    caminho_txt_saida = PASTA_SAIDA / f"{prefixo}.txt"

    # 1. Localizar áudio de origem
    audio_origem = localizar_audio_origem(sermon_id)
    if not audio_origem:
        return {
            "idx": idx,
            "sermon_id": sermon_id,
            "status": "ERRO_AUDIO_NAO_ENCONTRADO",
            "score": 0.0,
            "detalhes": f"Áudio de origem para {sermon_id} não foi localizado."
        }

    try:
        # 2. Fatiamento com AudioSlicerIO (FFmpeg Input Seek)
        slicer = AudioSlicerIO(str(audio_origem), sample_rate=44100)
        ok_slice = slicer.slice_and_export(start_sec, end_sec, str(caminho_mp3_saida))
        if not ok_slice or not caminho_mp3_saida.exists():
            return {
                "idx": idx,
                "sermon_id": sermon_id,
                "status": "ERRO_FFMPEG_SLICE",
                "score": 0.0,
                "detalhes": "Falha na exportação do segmento FFmpeg."
            }

        # 3. Análise DSP (librosa)
        dsp = DSPAnalyzer(str(caminho_mp3_saida))
        clip_ratio = dsp.detect_clipping_ratio(threshold=0.995)
        sil_ratio = dsp.calculate_silence_ratio(db_threshold=-40.0, hop_length=512)

        # 4. Análise NLP (spaCy)
        nlp_engine = TextCohesionNLP(nlp_instance=GLOBAL_NLP_INSTANCE)
        nlp_info = nlp_engine.analyze_sentence_completeness(texto_trecho)
        wpm = nlp_engine.calculate_wpm(texto_trecho, audio_duration_sec=duracao)

        # 5. Scoring Heurístico
        scorer = HeuristicScorer()
        score_data = scorer.compute_score(
            clip_ratio=clip_ratio,
            sil_ratio=sil_ratio,
            completeness=nlp_info["completeness"],
            wpm=wpm,
            last_pos=nlp_info["last_pos"]
        )

        # 6. Exportação do relatório .txt
        exportar_relatorio_txt(
            caminho_txt=caminho_txt_saida,
            nome_audio=caminho_mp3_saida.name,
            start_sec=start_sec,
            end_sec=end_sec,
            score_data=score_data,
            clip_ratio=clip_ratio,
            sil_ratio=sil_ratio,
            wpm=wpm,
            nlp_completeness=nlp_info["completeness"],
            diagnostico_nlp=nlp_info["diagnostico"],
            texto_trecho=texto_trecho
        )

        return {
            "idx": idx,
            "sermon_id": sermon_id,
            "status": score_data["status"],
            "score": score_data["final_score"],
            "wpm": wpm,
            "clipping_pct": clip_ratio * 100.0,
            "silence_pct": sil_ratio * 100.0,
            "mp3_path": str(caminho_mp3_saida),
            "txt_path": str(caminho_txt_saida)
        }

    except Exception as ex:
        err_msg = f"Exceção durante triagem do corte {idx}: {ex}"
        return {
            "idx": idx,
            "sermon_id": sermon_id,
            "status": "ERRO_PROCESSAMENTO",
            "score": 0.0,
            "detalhes": err_msg
        }


# =============================================================================
# 7. ORQUESTRADOR PRINCIPAL DA FASE 2.5
# =============================================================================

def main():
    garantir_dependencias()

    print("==========================================================================")
    print("🏛️  IBPM CR AUTOMATION SYSTEM — FASE 2.5 TRIAGEM QA & GERADOR DE AMOSTRAS")
    print("   • Fatiamento : ffmpeg-python (Input Seek -ss -to + libmp3lame 192k)")
    print("   • Engine DSP  : librosa (Clipping Ratio + RMS Silence Ratio em -40dB)")
    print("   • Engine NLP  : spaCy pt_core_news_lg (Parser de Dependência + WPM)")
    print("   • Scoring     : Heurística Multidimensional (Aprovado se Score >= 70.0)")
    print("==========================================================================\n")

    if not CSV_ENTRADA.exists():
        print(f"❌ Erro: Arquivo de cortes {CSV_ENTRADA} não foi encontrado!")
        sys.exit(1)

    PASTA_SAIDA.mkdir(parents=True, exist_ok=True)

    # Carregar registros do CSV da Fase 2
    with open(CSV_ENTRADA, "r", encoding="utf-8-sig") as f:
        linhas_csv = list(csv.DictReader(f))

    total_cortes = len(linhas_csv)
    print(f"📊 Registros de cortes carregados do CSV: {total_cortes}")
    print(f"📂 Diretório de saída para revisão local: {PASTA_SAIDA.resolve()}\n")

    if total_cortes == 0:
        print("⚠️ O CSV de entrada está vazio. Encerrando.")
        return

    # Preparar tarefas para os trabalhadores
    tasks = [(idx, row) for idx, row in enumerate(linhas_csv, start=1)]

    # Determinar número razoável de trabalhadores (limita a 4 para poupar RAM com spaCy/librosa)
    num_cpus = max(1, min(os.cpu_count() or 2, 4))
    print(f"🚀 Iniciando ProcessPoolExecutor paralelizado com {num_cpus} processos em paralelo...\n")

    start_time = time.time()
    aprovados = 0
    rejeitados = 0
    erros = 0

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

    elapsed = time.time() - start_time
    elapsed_str = time.strftime("%H:%M:%S", time.gmtime(elapsed))

    print("\n==========================================================================")
    print("🎉 FASE 2.5 — RELATÓRIO FINAL DE TRIAGEM E QUALITY ASSURANCE")
    print(f"   • Tempo total de execução: {elapsed_str}")
    print(f"   • Total de cortes analisados: {total_cortes}")
    print(f"   • Cortes APROVADOS  (Score >= 70): {aprovados} ({aprovados/total_cortes*100:.1f}%)")
    print(f"   • Cortes REJEITADOS (Score < 70) : {rejeitados} ({rejeitados/total_cortes*100:.1f}%)")
    print(f"   • Erros de I/O ou processamento  : {erros}")
    print(f"   • Artefatos salvos em           : {PASTA_SAIDA.resolve()}")
    print("==========================================================================")


if __name__ == "__main__":
    main()
