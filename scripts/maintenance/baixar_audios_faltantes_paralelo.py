import json
import shutil
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

out_dir = Path("data/audios_faltantes")
out_dir.mkdir(parents=True, exist_ok=True)

missing_files = json.loads(Path("data/faltantes_69.json").read_text(encoding="utf-8"))
print(f"Iniciando download acelerado em paralelo de {len(missing_files)} audios...")

def download_file(f_name):
    if (out_dir / f_name).exists():
        print(f"  [JA EXISTE] {f_name}")
        return
    res1 = subprocess.run(["rclone", "copy", f"meudrive:IBPM_CR_Cortes/audio_podcasts/{f_name}", str(out_dir)], capture_output=True)
    if not (out_dir / f_name).exists():
        subprocess.run(["rclone", "copy", f"meudrive:IBPM_CR_Cortes/06_Podcasts_Audio/{f_name}", str(out_dir)], capture_output=True)
    if (out_dir / f_name).exists():
        print(f"  [OK] Baixado: {f_name}")
    else:
        print(f"  [AVISO] Nao encontrado: {f_name}")

with ThreadPoolExecutor(max_workers=12) as executor:
    executor.map(download_file, missing_files)

local_audios = list(out_dir.glob("*"))
print(f"\n==============================================================")
print(f"DOWNLOAD CONCLUIDO! Total na pasta local: {len(local_audios)} / {len(missing_files)}")
print(f"==============================================================")

print("Compactando pasta de audios para audios_faltantes.zip...")
zip_path = shutil.make_archive("data/audios_faltantes", "zip", str(out_dir))
print(f"ZIP CRIADO COM SUCESSO EM: {zip_path}")
