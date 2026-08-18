import sys
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

REMOTE_PODCASTS = "meudrive:IBPM_CR_Cortes/audio_podcasts"
REMOTE_PRONTOS = "meudrive:IBPM_CR_Cortes/audios_com_transcricao_pronta"

print("📡 Verificando duplicatas de formato (.m4a vs .webm) em audio_podcasts...")
res = subprocess.run(["rclone", "lsf", REMOTE_PODCASTS], capture_output=True, text=True, encoding="utf-8")
files = [f.strip() for f in res.stdout.splitlines() if f.strip()]

stems_m4a = {Path(f).stem for f in files if f.endswith('.m4a')}
webm_para_mover = [f for f in files if f.endswith('.webm') and Path(f).stem in stems_m4a]

print(f"📊 Arquivos total em audio_podcasts: {len(files)}")
print(f"📦 Arquivos .webm duplicados que serão movidos: {len(webm_para_mover)}")

if webm_para_mover:
    from concurrent.futures import ThreadPoolExecutor, as_completed
    def mover(f_nome):
        origem = f"{REMOTE_PODCASTS}/{f_nome}"
        destino = f"{REMOTE_PRONTOS}/{f_nome}"
        subprocess.run(["rclone", "moveto", origem, destino], capture_output=True, text=True, encoding="utf-8")
        print(f"  • Movido duplicado: {f_nome}", flush=True)

    with ThreadPoolExecutor(max_workers=8) as executor:
        list(executor.map(mover, webm_para_mover))

print("✨ LIMPEZA DE DUPLICATAS FINALIZADA!")
