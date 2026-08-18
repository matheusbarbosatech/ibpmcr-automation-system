import sys
import os
import json
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REMOTE_PODCASTS = "meudrive:IBPM_CR_Cortes/audio_podcasts"
REMOTE_PROCESSADOS = "meudrive:IBPM_CR_Cortes/audio_podcasts_processados"
REMOTE_SAIDA_TXT = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_txt"

print("================================================================")
print("🎯 SEPARAR E MANTER APENAS ÁUDIOS PENDENTES NO GOOGLE DRIVE")
print("================================================================\n", flush=True)

# 1. Listar arquivos em audio_podcasts
print(f"📡 Listando áudios em {REMOTE_PODCASTS}...", flush=True)
res_podcasts = subprocess.run(["rclone", "lsf", REMOTE_PODCASTS], capture_output=True, text=True, encoding="utf-8")
if res_podcasts.returncode != 0:
    print(f"❌ Erro ao listar {REMOTE_PODCASTS}: {res_podcasts.stderr}")
    sys.exit(1)

arquivos_podcasts = [f.strip() for f in res_podcasts.stdout.splitlines() if f.strip() and not f.endswith("/")]
print(f"📁 Total de áudios encontrados em audio_podcasts: {len(arquivos_podcasts)}", flush=True)

# 2. Listar transcrições existentes (.txt) em transcricoes_whisper_txt
print(f"📡 Listando transcrições existentes em {REMOTE_SAIDA_TXT}...", flush=True)
res_txt = subprocess.run(["rclone", "lsf", REMOTE_SAIDA_TXT], capture_output=True, text=True, encoding="utf-8")
stems_transcritos = set()
if res_txt.returncode == 0:
    for item in res_txt.stdout.splitlines():
        item_str = item.strip()
        if item_str.endswith(".txt"):
            stems_transcritos.add(Path(item_str).stem)

print(f"📋 Total de transcrições .txt prontas encontradas: {len(stems_transcritos)}", flush=True)

# 3. Separar o que fica e o que deve ser movido
manter_no_drive = []
mover_para_processados = []

for arq in arquivos_podcasts:
    stem = Path(arq).stem
    if stem in stems_transcritos:
        mover_para_processados.append(arq)
    else:
        manter_no_drive.append(arq)

print(f"\n📊 Resultado da Análise:")
print(f"   • Áudios PENDENTES que FICARÃO em '{REMOTE_PODCASTS}': {len(manter_no_drive)}")
print(f"   • Áudios JÁ TRANSCRITOS a mover para '{REMOTE_PROCESSADOS}': {len(mover_para_processados)}", flush=True)

if not mover_para_processados:
    print("\n🎉 A pasta do Drive já contém APENAS os áudios pendentes!", flush=True)
    sys.exit(0)

# 4. Mover arquivos já transcrevidos em paralelo
print(f"\n🚀 Movendo {len(mover_para_processados)} áudios já transcrevidos para {REMOTE_PROCESSADOS}...", flush=True)

def mover_arquivo(item):
    idx, arq_nome = item
    origem = f"{REMOTE_PODCASTS}/{arq_nome}"
    destino = f"{REMOTE_PROCESSADOS}/{arq_nome}"
    cmd = ["rclone", "moveto", origem, destino]
    res_m = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    if res_m.returncode == 0:
        print(f"  [{idx}/{len(mover_para_processados)}] 📦 Movido: {arq_nome}", flush=True)
        return True
    else:
        print(f"  [{idx}/{len(mover_para_processados)}] ❌ Erro ao mover {arq_nome}: {res_m.stderr.strip()}", flush=True)
        return False

items = list(enumerate(mover_para_processados, start=1))
sucessos = 0
erros = 0

with ThreadPoolExecutor(max_workers=8) as executor:
    futures = [executor.submit(mover_arquivo, item) for item in items]
    for f in as_completed(futures):
        if f.result():
            sucessos += 1
        else:
            erros += 1

print(f"\n================================================================")
print(f"✨ ORGANIZAÇÃO DO GOOGLE DRIVE FINALIZADA!")
print(f"   • Sucessos: {sucessos}")
print(f"   • Erros:    {erros}")
print(f"   • A pasta '{REMOTE_PODCASTS}' agora possui APENAS os {len(manter_no_drive)} áudios pendentes!")
print(f"================================================================", flush=True)
