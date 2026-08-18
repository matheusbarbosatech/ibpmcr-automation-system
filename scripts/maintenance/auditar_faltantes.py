import sys
import re
import json
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
LOCAL_TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"

REMOTE_PODCASTS = "meudrive:IBPM_CR_Cortes/audio_podcasts"
REMOTE_P06 = "meudrive:IBPM_CR_Cortes/06_Podcasts_Audio"
REMOTE_PRONTOS = "meudrive:IBPM_CR_Cortes/audios_com_transcricao_pronta"
REMOTE_SAIDA_TXT = "meudrive:IBPM_CR_Cortes/transcricoes_whisper_txt"

print("================================================================")
print("🔍 AUDITORIA COMPLETA DE ÁUDIOS FALTANTES (DRIVE x LOCAL)")
print("================================================================\n", flush=True)

def extract_video_id(filename: str):
    m = re.search(r'_([a-zA-Z0-9_-]{11})_', filename) or re.search(r'^([a-zA-Z0-9_-]{11})', filename)
    return m.group(1) if m else None

# 1. Coletar todas as transcrições locais (.txt)
stems_concluidos = set()
ids_concluidos = set()

if LOCAL_TXT_DIR.exists():
    for f in LOCAL_TXT_DIR.glob("*.txt"):
        stems_concluidos.add(f.stem)
        vid = extract_video_id(f.name)
        if vid:
            ids_concluidos.add(vid)

print(f"📄 Transcrições Locais (.txt): {len(stems_concluidos)} arquivos | {len(ids_concluidos)} Video IDs únicos")

# 2. Coletar transcrições no Google Drive (transcricoes_whisper_txt)
res_drv_txt = subprocess.run(["rclone", "lsf", REMOTE_SAIDA_TXT], capture_output=True, text=True, encoding="utf-8")
if res_drv_txt.returncode == 0:
    for line in res_drv_txt.stdout.splitlines():
        line_str = line.strip()
        if line_str and line_str.endswith(".txt"):
            stems_concluidos.add(Path(line_str).stem)
            vid = extract_video_id(line_str)
            if vid:
                ids_concluidos.add(vid)

# 3. Coletar áudios já marcados como prontos no Drive
res_prontos = subprocess.run(["rclone", "lsf", REMOTE_PRONTOS], capture_output=True, text=True, encoding="utf-8")
if res_prontos.returncode == 0:
    for line in res_prontos.stdout.splitlines():
        line_str = line.strip()
        if line_str and not line_str.endswith("/"):
            stems_concluidos.add(Path(line_str).stem)
            vid = extract_video_id(line_str)
            if vid:
                ids_concluidos.add(vid)

print(f"📊 Total de transcrições/áudios concluídos acumulados: {len(stems_concluidos)} stems | {len(ids_concluidos)} Video IDs únicos\n")

# 4. Listar áudios em audio_podcasts
res_pod = subprocess.run(["rclone", "lsf", REMOTE_PODCASTS], capture_output=True, text=True, encoding="utf-8")
audios_pod = [f.strip() for f in res_pod.stdout.splitlines() if f.strip() and not f.endswith("/")] if res_pod.returncode == 0 else []

# 5. Listar áudios em 06_Podcasts_Audio
res_p06 = subprocess.run(["rclone", "lsf", REMOTE_P06], capture_output=True, text=True, encoding="utf-8")
audios_p06 = [f.strip() for f in res_p06.stdout.splitlines() if f.strip() and not f.endswith("/")] if res_p06.returncode == 0 else []

# Unificar lista de áudios
todos_audios_dict = {}
for a in audios_pod + audios_p06:
    todos_audios_dict[Path(a).name] = a

todos_audios = sorted(list(todos_audios_dict.keys()))
print(f"📁 Total de arquivos de áudio únicos no Drive: {len(todos_audios)}")

# 6. Filtrar faltantes
faltantes = []
for arq in todos_audios:
    vid_arq = extract_video_id(arq)
    stem_arq = Path(arq).stem
    
    if stem_arq in stems_concluidos:
        continue
    if vid_arq and vid_arq in ids_concluidos:
        continue
        
    faltantes.append(arq)

print(f"\n🎯 TOTAL EXATO DE ÁUDIOS FALTANTES REALMENTE PENDENTES: {len(faltantes)}")
print("================================================================")
for idx, item in enumerate(faltantes, start=1):
    print(f"[{idx:02d}/{len(faltantes):02d}] {item}")
print("================================================================")

# Salvar lista em data/lista_exata_faltantes.json
LISTA_OUT = BASE_DIR / "data" / "lista_exata_faltantes.json"
LISTA_OUT.parent.mkdir(parents=True, exist_ok=True)
with open(LISTA_OUT, "w", encoding="utf-8") as f_out:
    json.dump(faltantes, f_out, ensure_ascii=False, indent=2)

print(f"\n💾 Lista salva em: {LISTA_OUT.relative_to(BASE_DIR)}")
