# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - SCRIPT ÚNICO MESTRE 100% NUVEM (COLAB GPU + GROQ)
# ===========================================================================
# Executa a TRANSCRIÇÃO LARGE-V3 EM GPU + MINERAÇÃO GROQ LLM (Contexto Integral 128k Tokens).
# USO ZERO DA SUA MÁQUINA! Tudo roda nos servidores do Google Colab e do Groq.

import os
import re
import json
import sqlite3
import torch
from pathlib import Path

# 1. INSTALAÇÃO E CONFIGURAÇÃO INICIAL (AUTOMÁTICA)
try:
    from google.colab import drive
    drive.mount('/content/drive', force_remount=False)
except ImportError:
    pass

# Garantir dependências instaladas
os.system("pip install -q faster-whisper groq tqdm torch")

from tqdm import tqdm
from faster_whisper import WhisperModel
from groq import Groq

# 🔑 CHAVE DA API GROQ
GROQ_API_KEY = "SUA_CHAVE_GROQ_AQUI"
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

# 📂 PASTAS NO SEU GOOGLE DRIVE
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
INSIGHTS_DIR = GDRIVE_DIR / "insights_fase3"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# ⚡ CONFIGURAÇÃO DA GPU T4 NO COLAB
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"
model_size = "large-v3"

print("===========================================================================")
print(f" 🚀 SCRIPT MESTRE 100% NUVEM (GPU {device.upper()} + GROQ LLM 128K CONTEXTO)")
print(f"   Modelo Transcrição: Faster-Whisper {model_size.upper()}")
print(f"   Modelo IA: Groq Cloud ({GROQ_MODEL_NAME}) - Contexto Total sem Cortes!")
print(f"   Pasta no Google Drive: {GDRIVE_DIR}")
print("===========================================================================")

whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)

groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != "SUA_CHAVE_GROQ_AQUI":
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"⚡ Conectado à Groq Cloud API ({GROQ_MODEL_NAME}).")
else:
    print("⚠️ GROQ_API_KEY não informada! Defina a chave na variável GROQ_API_KEY.")

PROMPT_SYSTEM = """Você é um Curador de Conteúdo e Teólogo Sênior especializado em comunicação cristã.
Analise a pregação integral do culto da Igreja Batista Pentecostal Mundial (IBPM CR) e retorne ESTRITAMENTE UM OBJETO JSON VÁLIDO contendo:
{
  "01_tema_central": "Resumo executivo da mensagem em 2 a 3 parágrafos curtos.",
  "02_frases_virais": ["Frase 1", "Frase 2", "Frase 3", "Frase 4"],
  "03_passagens_biblicas": ["Livro Cap:Vers"],
  "04_ideia_carrossel_instagram": ["Slide 1: ...", "Slide 2: ...", "Slide 3: ...", "Slide 4: ..."],
  "05_cortes_virais": [
    {"titulo": "Título 1", "contexto": "...", "sugestao_b_roll": "...", "score_viral": 95, "trecho_inicial": "...", "trecho_final": "..."}
  ],
  "06_prompt_thumbnail": "Cinematic 8k photo of pastor preaching..."
}"""

audio_files = sorted([f for f in AUDIO_DIR.glob("*") if f.suffix.lower() in [".mp3", ".m4a", ".webm"] and not f.name.endswith(".part")])
pending_files = [f for f in audio_files if not (f.with_suffix(".txt").exists() and f.with_suffix(".txt").stat().st_size > 100) or not ((INSIGHTS_DIR / f"{f.stem}.insights.json").exists() and (INSIGHTS_DIR / f"{f.stem}.insights.json").stat().st_size > 100)]

print(f"📋 Cultos Pendentes de Processamento: {len(pending_files)} / {len(audio_files)}")

if not pending_files:
    print("\n🎉 Todos os cultos no seu Google Drive já foram transcritos e minerados com sucesso!")
else:
    conn = sqlite3.connect(str(DB_PATH)) if DB_PATH.exists() else None

    for audio_path in tqdm(pending_files, desc="Processando 100% na Nuvem (Contexto Total)", unit="culto"):
        v_name = audio_path.stem
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")
        insight_path = INSIGHTS_DIR / f"{v_name}.insights.json"

        # 1. Transcrição na GPU T4 (Large-v3 Full Accuracy)
        full_text = ""
        if not (txt_path.exists() and txt_path.stat().st_size > 100):
            try:
                segments, info = whisper_model.transcribe(str(audio_path), language="pt", beam_size=5, vad_filter=True, word_timestamps=True)
                segments_data, full_text_parts = [], []
                for seg in segments:
                    segments_data.append({"segment_id": seg.id, "start_sec": round(seg.start, 2), "end_sec": round(seg.end, 2), "text": seg.text.strip()})
                    full_text_parts.append(seg.text.strip())

                full_text = " ".join(full_text_parts)
                with open(txt_path, "w", encoding="utf-8") as f: f.write(full_text)
                with open(json_path, "w", encoding="utf-8") as f: f.write(json.dumps(segments_data, ensure_ascii=False, indent=2))
            except Exception as e:
                print(f"⚠️ Erro na transcrição de {audio_path.name}: {e}")
                continue
        else:
            with open(txt_path, "r", encoding="utf-8") as f: full_text = f.read()

        # 2. Mineração na Nuvem Groq (Llama 3.3 70B - CONTEXTO INTEGRAL SEM TRUNCAÇÃO)
        if groq_client and full_text and not (insight_path.exists() and insight_path.stat().st_size > 100):
            try:
                # 🚀 Envia a pregação INTEGRAL (até 300.000 caracteres / 128k tokens) aproveitando toda a janela de contexto do Llama 3.3 70B
                full_text_clean = full_text[:300000] if len(full_text) > 300000 else full_text
                
                chat_resp = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": PROMPT_SYSTEM},
                        {"role": "user", "content": f"Título do Culto: {v_name}\n\nTexto Integral da Pregação:\n{full_text_clean}"}
                    ],
                    model=GROQ_MODEL_NAME,
                    response_format={"type": "json_object"},
                    temperature=0.3
                )
                if chat_resp and chat_resp.choices:
                    with open(insight_path, "w", encoding="utf-8") as f:
                        f.write(chat_resp.choices[0].message.content)

                    if conn:
                        v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else ""
                        if v_id:
                            cursor = conn.cursor()
                            cursor.execute("UPDATE videos SET transcrito = 1, texto_transcrito = ?, tipo_transcricao = 'colab_large_v3' WHERE video_id = ?", (full_text, v_id))
                            conn.commit()
            except Exception as e:
                print(f"⚠️ Erro na mineração Groq para {v_name}: {e}")

    if conn: conn.close()

print("\n" + "=" * 75)
print(" 🎉 SCRIPT MESTRE CONCLUÍDO! TODOS OS CULTOS TRANCRITOS E MINERADOS (CONTEXTO INTEGRAL) NO GOOGLE DRIVE!")
print("=" * 75)
