import os
import sys
import json
import subprocess
from pathlib import Path

# 1. Instalar dependências necessárias no ambiente Linux do Kaggle
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "faster-whisper"], check=True)

# Instalar o executável binário do rclone no Linux do Kaggle
print("Instalando rclone no sistema Linux do Kaggle...")
subprocess.run("curl -s https://rclone.org/install.sh | bash", shell=True, check=True)

from faster_whisper import WhisperModel

# 2. Configurar a conexão do Rclone no Kaggle com o seu Google Drive
RCLONE_CONFIG_DIR = Path("/root/.config/rclone")
RCLONE_CONFIG_DIR.mkdir(parents=True, exist_ok=True)

RCLONE_TOKEN_JSON = os.environ.get("RCLONE_TOKEN", '{"access_token":"YOUR_ACCESS_TOKEN","token_type":"Bearer","refresh_token":"YOUR_REFRESH_TOKEN"}')
RCLONE_CONF_CONTENT = f"""[meudrive]
type = drive
scope = drive
token = {RCLONE_TOKEN_JSON}
"""

with open(RCLONE_CONFIG_DIR / "rclone.conf", "w", encoding="utf-8") as f:
    f.write(RCLONE_CONF_CONTENT)

print("Rclone configurado no Kaggle para acessar seu Google Drive!")

# 3. Configurar caminhos temporários no Kaggle
KAGGLE_AUDIOS_DIR = Path("/kaggle/working/audios")
KAGGLE_TXT_DIR = Path("/kaggle/working/transcricoes_txt")
KAGGLE_JSON_DIR = Path("/kaggle/working/transcricoes_json")

KAGGLE_AUDIOS_DIR.mkdir(parents=True, exist_ok=True)
KAGGLE_TXT_DIR.mkdir(parents=True, exist_ok=True)
KAGGLE_JSON_DIR.mkdir(parents=True, exist_ok=True)

REMOTE_PODCASTS = "meudrive:IBPM_CR_Cortes/audio_podcasts"
REMOTE_SAIDA_TXT = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_txt"
REMOTE_SAIDA_JSON = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_json"

print("================================================================")
print("TRANSCRIÇÃO ACELERADA EM GPU T4 (KAGGLE) VIA FASTER-WHISPER")
print("================================================================\n", flush=True)

# 4. Baixar transcrições já existentes no Drive para não re-transcrever o que já foi feito
print(f"Verificando transcricoes ja existentes em {REMOTE_SAIDA_TXT}...", flush=True)
subprocess.run(["rclone", "copy", REMOTE_SAIDA_TXT, str(KAGGLE_TXT_DIR)])
txts_existentes = set(f.stem for f in KAGGLE_TXT_DIR.glob("*.txt"))
print(f"Transcrições já concluídas anteriormente: {len(txts_existentes)}", flush=True)

# 5. Baixar áudios do Google Drive para o Kaggle
print(f"\nBaixando audios de {REMOTE_PODCASTS} para o Kaggle...", flush=True)
subprocess.run([
    "rclone", "copy", REMOTE_PODCASTS, str(KAGGLE_AUDIOS_DIR),
    "-P", "--transfers", "8", "--checkers", "8"
])

audios_todos = sorted(
    list(KAGGLE_AUDIOS_DIR.glob("*.m4a")) + 
    list(KAGGLE_AUDIOS_DIR.glob("*.webm")) + 
    list(KAGGLE_AUDIOS_DIR.glob("*.mp4"))
)

# Filtrar apenas os áudios PENDENTES
audios_pendentes = [arq for arq in audios_todos if arq.stem not in txts_existentes]

print(f"\nTotal de audios no Drive: {len(audios_todos)}")
print(f"Audios ja transcrevidos (ignorados): {len(txts_existentes)}")
print(f"Audios PENDENTES para transcrever agora: {len(audios_pendentes)}", flush=True)

if not audios_pendentes:
    print("\nTodos os audios ja foram transcritos! Nenhum pendente.", flush=True)
    sys.exit(0)

# 6. Carregar Modelo Faster-Whisper na GPU CUDA ('medium' com float16)
MODEL_SIZE = "medium"
print(f"\nCarregando modelo Faster-Whisper '{MODEL_SIZE}' na GPU CUDA (float16)...", flush=True)
model = WhisperModel(MODEL_SIZE, device="cuda", compute_type="float16")
print("Modelo carregado com sucesso na GPU T4!", flush=True)

# 7. Processar APENAS os áudios pendentes na GPU T4
sucessos = 0
erros = 0

for idx, arq in enumerate(audios_pendentes, start=1):
    nome_stem = arq.stem
    caminho_txt = KAGGLE_TXT_DIR / f"{nome_stem}.txt"
    caminho_json = KAGGLE_JSON_DIR / f"{nome_stem}.json"
    
    print(f"\n[{idx}/{len(audios_pendentes)}] Transcrevendo na GPU T4: {arq.name}...", flush=True)
    
    try:
        segments, info = model.transcribe(str(arq), language="pt", beam_size=5)
        
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
        
        # Salvar .txt no Kaggle
        with open(caminho_txt, "w", encoding="utf-8") as f_txt:
            f_txt.write(texto_final)
            
        # Salvar .json no Kaggle
        with open(caminho_json, "w", encoding="utf-8") as f_json:
            json.dump({
                "file": arq.name,
                "language": info.language,
                "duration": round(info.duration, 2),
                "words_count": words_count,
                "text": texto_final,
                "segments": segmentos_json
            }, f_json, ensure_ascii=False, indent=2)
            
        print(f"   Concluido em GPU T4! Duracao: {info.duration:.1f}s | Palavras: {words_count}")
        
        # Enviar transcrição (.txt e .json) de volta ao Google Drive imediatamente
        subprocess.run(["rclone", "copy", str(caminho_txt), REMOTE_SAIDA_TXT], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(["rclone", "copy", str(caminho_json), REMOTE_SAIDA_JSON], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print(f"   Sincronizado no Google Drive!", flush=True)
        
        sucessos += 1
        
    except Exception as err:
        print(f"   Erro ao transcrever {arq.name}: {err}", flush=True)
        erros += 1

print(f"\n================================================================")
print(f"TRANSCRIÇÃO EM GPU T4 NO KAGGLE FINALIZADA!")
print(f"   • Sucessos: {sucessos}")
print(f"   • Erros:    {erros}")
print(f"================================================================", flush=True)
