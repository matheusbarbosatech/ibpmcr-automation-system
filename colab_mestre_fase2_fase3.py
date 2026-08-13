# ===========================================================================
# 🚀 IBPM CR AUTOMATION SYSTEM - SCRIPT ÚNICO MESTRE 100% NUVEM (COLAB GPU + GROQ)
# ===========================================================================
# Executa a TRANSCRIÇÃO LARGE-V3 EM GPU + MINERAÇÃO GROQ LLM em 1 ÚNICO BLOCO.
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

# 🔑 CHAVE DA API GROQ (Cole sua chave do Groq entre as aspas abaixo)
GROQ_API_KEY = "SUA_CHAVE_GROQ_AQUI"
GROQ_MODEL_NAME = "llama-3.3-70b-versatile"

# 📂 DIRETO NO SEU GOOGLE DRIVE
GDRIVE_DIR = Path("/content/drive/MyDrive/IBPM_CR_Cortes")
AUDIO_DIR = GDRIVE_DIR / "audio_podcasts"
INSIGHTS_DIR = GDRIVE_DIR / "insights_fase3"
DB_PATH = GDRIVE_DIR / "ibpmcr_master.db"

# Garantir criação da pasta de insights no Drive
INSIGHTS_DIR.mkdir(parents=True, exist_ok=True)

# ⚡ CONFIGURAÇÃO DA GPU T4 NO COLAB
device = "cuda" if torch.cuda.is_available() else "cpu"
compute_type = "float16" if device == "cuda" else "float32"
model_size = "large-v3"

print("===========================================================================")
print(" 🚀 INICIANDO SCRIPT ÚNICO MESTRE 100% NUVEM (COLAB GPU + GROQ LLM)")
print(f"   GPU Colab: {device.upper()} | Modelo Transcrição: Faster-Whisper {model_size.upper()}")
print(f"   Modelo IA: Groq Cloud ({GROQ_MODEL_NAME})")
print(f"   Pasta no Google Drive: {GDRIVE_DIR}")
print("===========================================================================")

if not AUDIO_DIR.exists():
    raise FileNotFoundError(f"❌ Pasta {AUDIO_DIR} não encontrada no Google Drive. Verifique se os áudios já foram enviados!")

# Carrega modelo de transcrição na GPU
print(f"\n⚡ [1/2] Carregando modelo Faster-Whisper '{model_size}' na GPU T4...")
whisper_model = WhisperModel(model_size, device=device, compute_type=compute_type)

# Conecta à API do Groq
groq_client = None
if GROQ_API_KEY and GROQ_API_KEY != "SUA_CHAVE_GROQ_AQUI":
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"⚡ [2/2] Conectado à Groq Cloud API ({GROQ_MODEL_NAME}).")
else:
    print("⚠️ GROQ_API_KEY não foi informada na variável GROQ_API_KEY! Apenas as transcrições serão salvas.")

PROMPT_SYSTEM = """Você é um Curador de Conteúdo e Teólogo Sênior especializado em comunicação cristã.
Analise a pregação do culto da Igreja Batista Pentecostal Mundial (IBPM CR) e retorne ESTRITAMENTE UM OBJETO JSON VÁLIDO contendo:
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

# Lista todos os cultos no Drive
all_files = sorted(list(AUDIO_DIR.glob("*")))
audio_files = [f for f in all_files if f.suffix.lower() in [".mp3", ".m4a", ".webm"] and not f.name.endswith(".part")]

print(f"\n📂 Total de cultos encontrados no Google Drive: {len(audio_files)}")

# Filtra cultos pendentes (falta .txt OU falta .insights.json)
pending_files = []
for a_path in audio_files:
    txt_path = a_path.with_suffix(".txt")
    insight_path = INSIGHTS_DIR / f"{a_path.stem}.insights.json"
    
    if not (txt_path.exists() and txt_path.stat().st_size > 100) or not (insight_path.exists() and insight_path.stat().st_size > 100):
        pending_files.append(a_path)

print(f"📋 Cultos Pendentes de Processamento Mestre: {len(pending_files)} / {len(audio_files)}")

if not pending_files:
    print("\n🎉 Todos os cultos no seu Google Drive já foram transcritos e minerados com sucesso!")
else:
    # Conexão com SQLite no Drive
    conn = None
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))

    pbar = tqdm(pending_files, desc="Processando Mestre (GPU + Groq)", unit="culto")

    for audio_path in pbar:
        v_name = audio_path.stem
        txt_path = audio_path.with_suffix(".txt")
        json_path = audio_path.with_suffix(".json")
        insight_path = INSIGHTS_DIR / f"{v_name}.insights.json"

        pbar.set_postfix_str(v_name[:25])

        # 🎙️ FASE 2: TRANSCRIÇÃO INTEGRAL NA GPU (Large-v3)
        full_text = ""
        segments_json_str = ""

        if not (txt_path.exists() and txt_path.stat().st_size > 100):
            try:
                segments, info = whisper_model.transcribe(
                    str(audio_path),
                    language="pt",
                    beam_size=5,
                    vad_filter=True,
                    word_timestamps=True
                )
                segments_data, full_text_parts = [], []
                for seg in segments:
                    segments_data.append({
                        "segment_id": seg.id,
                        "start_sec": round(seg.start, 2),
                        "end_sec": round(seg.end, 2),
                        "text": seg.text.strip()
                    })
                    full_text_parts.append(seg.text.strip())

                full_text = " ".join(full_text_parts)
                segments_json_str = json.dumps(segments_data, ensure_ascii=False, indent=2)

                # Salva .txt e .json no Drive
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(full_text)
                with open(json_path, "w", encoding="utf-8") as f:
                    f.write(segments_json_str)

            except Exception as e:
                print(f"\n⚠️ Erro ao transcrever {audio_path.name}: {e}")
                continue
        else:
            with open(txt_path, "r", encoding="utf-8") as f:
                full_text = f.read()

        # 🧠 FASE 3: MINERAÇÃO DE CONTEÚDO VIA GROQ LLM (Llama 3.3 70B)
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
                    raw_insight_json = chat_resp.choices[0].message.content
                    with open(insight_path, "w", encoding="utf-8") as f:
                        f.write(raw_insight_json)

                    # Atualiza SQLite se presente
                    if conn:
                        v_id = v_name.split("_")[2] if len(v_name.split("_")) > 2 else ""
                        if v_id:
                            cursor = conn.cursor()
                            cursor.execute("""
                            UPDATE videos SET transcrito = 1, texto_transcrito = ?, tipo_transcricao = 'colab_large_v3' WHERE video_id = ?
                            """, (full_text, v_id))
                            conn.commit()

            except Exception as e:
                print(f"\n⚠️ Erro na mineração Groq para {v_name}: {e}")

    if conn:
        conn.close()

    print("\n" + "=" * 75)
    print(" 🎉 SCRIPT ÚNICO MESTRE 100% NUVEM CONCLUÍDO COM SUCESSO!")
    print(" Todos os arquivos de transcrição, cortes e insights foram salvos no Google Drive.")
    print("=" * 75)
