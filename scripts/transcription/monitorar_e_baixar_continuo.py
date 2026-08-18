import sys
import time
import subprocess
from pathlib import Path

# Configurar UTF-8 no Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"
LOCAL_JSON_DIR = BASE_DIR / "data" / "transcriptions" / "json"

REMOTE_TXT = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_txt"
REMOTE_JSON = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_json"
TOTAL_META = 455  # Total de cultos catalogados da IBPM

print("==========================================================================")
print("🔄 MONITOR DE DOWNLOAD CONTÍNUO E AUTÔNOMO DAS TRANSCRIÇÕES (CONTA 1 & 2)")
print("==========================================================================\n", flush=True)

# Garantir que as pastas locais existem
LOCAL_TXT_DIR.mkdir(parents=True, exist_ok=True)
LOCAL_JSON_DIR.mkdir(parents=True, exist_ok=True)

contagem_anterior = len(list(LOCAL_TXT_DIR.glob("*.txt")))
print(f"📊 Contagem Inicial Local: {contagem_anterior}/{TOTAL_META} transcrições\n", flush=True)

def sincronizar_drive():
    # 1. Copiar novos arquivos TXT do Google Drive para o disco local
    subprocess.run(
        ["rclone", "copy", REMOTE_TXT, str(LOCAL_TXT_DIR), "--transfers", "16"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    # 2. Copiar novos arquivos JSON do Google Drive para o disco local
    subprocess.run(
        ["rclone", "copy", REMOTE_JSON, str(LOCAL_JSON_DIR), "--transfers", "16"],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )

cycle = 0
while True:
    try:
        sincronizar_drive()
        
        txt_atuais = set(f.stem for f in LOCAL_TXT_DIR.glob("*.txt"))
        json_atuais = set(f.stem for f in LOCAL_JSON_DIR.glob("*.json"))
        
        contagem_atual = len(txt_atuais)
        novos = contagem_atual - contagem_anterior
        
        cycle += 1
        
        if novos > 0:
            print(f"✨ [{time.strftime('%H:%M:%S')}] +{novos} NOVA(S) TRANSCRIÇÃO(ÕES) BAIXADA(S)! Total Local: {contagem_atual}/{TOTAL_META}", flush=True)
            contagem_anterior = contagem_atual
        else:
            if cycle % 3 == 0:
                print(f"⏳ [{time.strftime('%H:%M:%S')}] Sincronizado. Progresso Local: {contagem_atual}/{TOTAL_META} (Faltam {TOTAL_META - contagem_atual})", flush=True)
        
        # Verificar se atingimos 100% dos cultos
        if contagem_atual >= TOTAL_META:
            print("\n" + "=" * 80, flush=True)
            print(f"🎉 CELEBRAÇÃO! TODAS AS {contagem_atual} TRANSCRIÇÕES ESTÃO NA SUA MÁQUINA LOCAL!", flush=True)
            print("=" * 80 + "\n", flush=True)
            break
            
    except Exception as err:
        print(f"⚠️ Aviso no monitoramento: {err}", flush=True)
        
    time.sleep(20)
