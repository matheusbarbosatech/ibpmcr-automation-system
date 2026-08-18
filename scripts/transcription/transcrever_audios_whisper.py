import sys
import os
import json
import shutil
import subprocess
from pathlib import Path
from faster_whisper import WhisperModel

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
PASTA_AUDIOS_PENDENTES = BASE_DIR / "data" / "raw" / "pendentes"
PASTA_AUDIOS_PROCESSADOS = BASE_DIR / "data" / "raw" / "processados"
PASTA_TXT = BASE_DIR / "data" / "transcriptions" / "txt"
PASTA_JSON = BASE_DIR / "data" / "transcriptions" / "json"
DATASET_INDEX_FILE = BASE_DIR / "data" / "transcriptions" / "dataset.json"

REMOTE_PODCASTS = "meudrive:IBPM_CR_Cortes/audio_podcasts"
REMOTE_SAIDA_TXT = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_txt"

PASTA_AUDIOS_PENDENTES.mkdir(parents=True, exist_ok=True)
PASTA_AUDIOS_PROCESSADOS.mkdir(parents=True, exist_ok=True)
PASTA_TXT.mkdir(parents=True, exist_ok=True)
PASTA_JSON.mkdir(parents=True, exist_ok=True)

print("================================================================")
print("🎙️ SISTEMA DE TRANSCRIÇÃO AUTOMÁTICA VIA WHISPER (FASTER-WHISPER)")
print("================================================================\n", flush=True)

# 1. Sincronizar áudios do Google Drive para a pasta de pendentes
print(f"📡 Verificando se há áudios no Google Drive ({REMOTE_PODCASTS})...", flush=True)
res_drive = subprocess.run(["rclone", "lsf", REMOTE_PODCASTS], capture_output=True, text=True, encoding="utf-8")
arquivos_drive = [f.strip() for f in res_drive.stdout.splitlines() if f.strip()]
print(f"📁 Encontrados {len(arquivos_drive)} áudios cadastrados no Drive.", flush=True)

if arquivos_drive:
    print(f"⬇️ Sincronizando áudios pendentes do Drive para {PASTA_AUDIOS_PENDENTES}...", flush=True)
    subprocess.run([
        "rclone", "copy", REMOTE_PODCASTS, str(PASTA_AUDIOS_PENDENTES),
        "-P", "--transfers", "4", "--checkers", "4"
    ])

# 2. Listar áudios pendentes
audios_locais = sorted(
    list(PASTA_AUDIOS_PENDENTES.glob("*.m4a")) + 
    list(PASTA_AUDIOS_PENDENTES.glob("*.webm")) + 
    list(PASTA_AUDIOS_PENDENTES.glob("*.mp4"))
)
print(f"\n📊 Total de áudios pendentes locais: {len(audios_locais)}", flush=True)

# Filtrar aqueles que ainda não têm arquivo .txt finalizado
audios_para_transcrever = []
for arq in audios_locais:
    caminho_txt = PASTA_TXT / f"{arq.stem}.txt"
    if not caminho_txt.exists():
        audios_para_transcrever.append(arq)
    else:
        # Se já existe TXT, mover áudio diretamente para processados
        shutil.move(str(arq), str(PASTA_AUDIOS_PROCESSADOS / arq.name))

print(f"🎯 Áudios a transcrever nesta rodada: {len(audios_para_transcrever)}", flush=True)

if not audios_para_transcrever:
    print("\n🎉 Todos os áudios já foram transcritos e organizados com sucesso!", flush=True)
    sys.exit(0)

# 3. Inicializar Modelo Faster-Whisper
print("\n⚙️ Carregando modelo Faster-Whisper ('small', int8)...", flush=True)
model = WhisperModel("small", device="cpu", compute_type="int8")
print("✅ Modelo Whisper carregado com sucesso!", flush=True)

# Carregar catálogo existente ou iniciar novo
dataset_index = []
if DATASET_INDEX_FILE.exists():
    try:
        with open(DATASET_INDEX_FILE, "r", encoding="utf-8") as f_idx:
            dataset_index = json.load(f_idx)
    except Exception:
        dataset_index = []

sucessos = 0
erros = 0

# 4. Processar transcrições uma a uma com acompanhamento em tempo real
for idx, arq_audio in enumerate(audios_para_transcrever, start=1):
    nome_stem = arq_audio.stem
    caminho_txt = PASTA_TXT / f"{nome_stem}.txt"
    caminho_json = PASTA_JSON / f"{nome_stem}.json"
    
    print(f"\n[{idx}/{len(audios_para_transcrever)}] 🎙️ Transcrevendo: {arq_audio.name}...", flush=True)
    
    try:
        segments, info = model.transcribe(str(arq_audio), language="pt", beam_size=5)
        
        texto_completo = []
        segmentos_json = []
        
        for segment in segments:
            texto_completo.append(segment.text.strip())
            segmentos_json.append({
                "start": round(segment.start, 2),
                "end": round(segment.end, 2),
                "text": segment.text.strip()
            })
            
        texto_final = " ".join(texto_completo)
        words_count = len(texto_final.split())
        
        # 1. Salvar .txt em data/transcriptions/txt/
        with open(caminho_txt, "w", encoding="utf-8") as f_txt:
            f_txt.write(texto_final)
            
        # 2. Salvar .json em data/transcriptions/json/
        payload_json = {
            "file": arq_audio.name,
            "language": info.language,
            "duration": round(info.duration, 2),
            "words_count": words_count,
            "text": texto_final,
            "segments": segmentos_json
        }
        with open(caminho_json, "w", encoding="utf-8") as f_json:
            json.dump(payload_json, f_json, ensure_ascii=False, indent=2)
            
        # 3. Atualizar dataset_index.json
        dataset_index.append({
            "file": arq_audio.name,
            "stem": nome_stem,
            "duration": round(info.duration, 2),
            "words_count": words_count,
            "txt_path": str(caminho_txt.relative_to(BASE_DIR)),
            "json_path": str(caminho_json.relative_to(BASE_DIR))
        })
        with open(DATASET_INDEX_FILE, "w", encoding="utf-8") as f_idx:
            json.dump(dataset_index, f_idx, ensure_ascii=False, indent=2)
            
        # 4. Mover áudio de data/raw/pendentes -> data/raw/processados
        destino_audio = PASTA_AUDIOS_PROCESSADOS / arq_audio.name
        shutil.move(str(arq_audio), str(destino_audio))
        
        print(f"   ✅ Transcrição Concluída!")
        print(f"   ⏱️ Duração: {info.duration:.1f}s | Palavras: {words_count}")
        print(f"   📁 Organizado em: data/transcriptions/txt/ & json/")
        print(f"   📦 Áudio movido para: data/raw/processados/", flush=True)
        
        # 5. Enviar TXT imediatamente para o Google Drive
        subprocess.run(["rclone", "copy", str(caminho_txt), REMOTE_SAIDA_TXT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   ☁️ Sincronizado no Google Drive!", flush=True)
        
        sucessos += 1
        
    except Exception as err:
        print(f"   ❌ Erro ao transcrever {arq_audio.name}: {err}", flush=True)
        erros += 1

print(f"\n================================================================")
print(f"✨ PROCESSAMENTO WHISPER FINALIZADO!")
print(f"   • Sucessos: {sucessos}")
print(f"   • Erros:    {erros}")
print(f"================================================================", flush=True)
