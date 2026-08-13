# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - CADERNO MESTRE 100% NUVEM (GOOGEL COLAB + GROQ)
# ===========================================================================
# Este script executa a TRANSCRIÇÃO LARGE-V3 EM GPU e a MINERAÇÃO GROQ LLM
# 100% nos servidores da nuvem do Google Colab e do Groq (USO ZERO DA SUA MÁQUINA!).
#
# 📋 INSTRUÇÕES NO COLAB:
# 1. Menu: Editar -> Configurações do ambiente de execução -> GPU T4 -> Salvar
# 2. Execute a Célula 1 e a Célula 2 abaixo.

# ---------------------------------------------------------------------------
# CÉLULA 1: Montar Google Drive e Instalar Dependências
# ---------------------------------------------------------------------------
"""
from google.colab import drive
drive.mount('/content/drive')

!pip install -q faster-whisper groq tqdm torch
"""

# ---------------------------------------------------------------------------
# CÉLULA 2: Execução Mestre 100% Nuvem (Transcrição GPU Large-v3 + Groq LLM)
# ---------------------------------------------------------------------------
import os
import re
import json
import sqlite3
import torch
from pathlib import Path
from tqdm import tqdm
from faster_whisper import WhisperModel
from groq import Groq

# 🔑 INSIRA SUA CHAVE DA GROQ API ABAIXO (Obtenha grátis em: https://console.groq.com/keys)
GROQ_API_KEY = "SUA_CHAVE_GROQ_AQUI"
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

# 📂 Caminhos no Google Drive Montado
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
INSIGHTS_DIR = GDRIVE_DIR / "insights_fase3"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

# Garantir que as pastas existam no Drive
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# ⚡ Configuração da GPU T4
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"
model_size = "large-v3"

print("===========================================================================")
print(" 🚀 INICIANDO PROCESSAMENTO MESTRE 100% NUVEM (COLAB GPU + GROQ LLM)")
print(f"   GPU Colab: {device.upper()} | Modelo Transcrição: Faster-Whisper {model_size.upper()}")
print(f"   Modelo IA: Groq Cloud ({GROQ_MODEL_NAME})")
print(f"   Pasta no Drive: {GDRIVE_DIR}")
print("===========================================================================")

if not AUDIO_DIR.exists():
    raise FileNotFoundError(f"❌ Pasta {AUDIO_DIR} não encontrada. Aguarde o Rclone enviar os áudios para o Drive!")

# Inicializa o modelo de transcrição na GPU
print(f"\n⚡ [COLAB GPU] Carregando modelo Faster-Whisper '{model_size}' de máxima precisão na GPU T4...")
whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)

# Inicializa o cliente da Groq API
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != "SUA_CHAVE_GROQ_AQUI":
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"⚡ [GROQ CLOUD] Conectado à API do Groq ({GROQ_MODEL_NAME}).")
else:
    print("⚠️ GROQ_API_KEY não configurada na Célula! Apenas as transcrições serão salvas.")

PROMPT_SYSTEM = """Você é um Curador de Conteúdo e Teólogo Sênior especializado em comunicação cristã.
Analise a pregação e retorne ESTRITAMENTE UM JSON VÁLIDO contendo:
"01_tema_central", "02_frases_virais" (4 frases), "03_passagens_biblicas", "04_ideia_carrossel_instagram" (4 slides), "05_cortes_virais" (3 cortes com titulo, contexto, sugestao_b_roll, score_viral 0-100, trecho_inicial, trecho_final), "06_prompt_thumbnail" (em inglês para Midjourney)."""

# Lista os arquivos no Drive
all_files = sorted(list(AUDIO_DIR.glob("*")))
audio_files = [f for f in all_files if f.suffix.lower() in [".mp3", ".m4a", ".webm"] and not f.name.endswith(".part")]

print(f"\n📂 Total de cultos encontrados no Drive: {len(audio_files)}")

# Filtra cultos pendentes
pending_files = []
for a_path in audio_files:
    txt_path = a_path.with_suffix(".txt")
    insight_path = INSIGHTS_DIR / f"{a_path.stem}.insights.json"
    
    # Se falta .txt OU falta o insight .json, adiciona na fila
    if not (txt_path.exists() and txt_path.stat().st_size > 100) or not (insight_path.exists() and insight_path.stat().st_size > 100):
        pending_files.append(a_path)

print(f"📋 Cultos Pendentes de Processamento Integral: {len(pending_files)} / {len(audio_files)}")

if not pending_files:
    print("\n🎉 Todos os cultos no seu Google Drive já estão transcritos e minerados com sucesso!")
else:
    pbar = tqdm(pending_files, desc="Processando 100% na Nuvem", unit="culto")

    for audio_path in pbar:
        v_name = audio_path.stem
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")
        insight_path = INSIGHTS_DIR / f"{v_name}.insights.json"

        pbar.set_postfix_str(v_name[:25])

        # 1. TRANSCRIÇÃO GPU (Large-v3) se ainda não existir .txt no Drive
        full_text = ""
        if not (txt_path.exists() and txt_path.stat().st_size > 100):
            try:
                segments, info = whisper_model.transcribe(str(audio_path), language="pt", beam_size=5, vad_filter=True, word_timestamps=True)
                segments_data, full_text_parts = [], []
                for seg in segments:
                    segments_data.append({"segment_id": seg.id, "start_sec": round(seg.start, 2), "end_sec": round(seg.end, 2), "text": seg.text.strip()})
                    full_text_parts.append(seg.text.strip())

                full_text = " ".join(full_text_parts)
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(json.dumps(segments_data, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"\n⚠️ Erro ao transcrever {audio_path.name}: {e}")
                continue
        else:
            with open(txt_path, "r", encoding="utf-8") as f:
                full_text = f.read()

        # 2. MINERAÇÃO GROQ LLM (Llama 3.3 70B) se ainda não existir .insights.json no Drive
        if groq_client and full_text and not (insight_path.exists() and insight_path.stat().st_size > 100):
            try:
                chat_resp = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": PROMPT_SYSTEM},
                        {"role": "user", "content": f"Título do Culto: {v_name}\n\nPregação:\n{full_text[:25000]}"}
                    ],
                    model=GROQ_MODEL_NAME,
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                if chat_resp and chat_resp.choices:
                    resp_str = chat_resp.choices[0].message.content
                    with open(insight_path, "w", encoding="utf-8") as f:
                        f.write(resp_str)
            except Exception as e:
                print(f"\n⚠️ Erro na mineração via Groq para {v_name}: {e}")

    print("\n" + "=" * 75)
    print(" 🎉 PROCESSAMENTO MESTRE 100% NUVEM CONCLUÍDO COM SUCESSO!")
    print(f" Todos os arquivos .txt, .json e .insights.json foram salvos no seu Google Drive:")
    print(f" 📂 Transcrições: {AUDIO_DIR}")
    print(f" 📂 Insights:     {INSIGHTS_DIR}")
    print("=" * 75)
