import json
import shutil
import subprocess
from pathlib import Path

# 1. Configurar diretórios
BASE_DIR = Path(__file__).resolve().parent.parent.parent
TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"
AUDIOS_LOCAL_DIR = BASE_DIR / "data" / "audios_faltantes"
DESKTOP_DIR = Path(r"C:\Users\matheus\Desktop\audios_faltantes_ibpm")
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

# 2. Carregar lista de 69 faltantes originais
FALTANTES_JSON = BASE_DIR / "data" / "faltantes_69.json"
missing_69 = json.loads(FALTANTES_JSON.read_text(encoding="utf-8"))

# 3. Mapear transcrições locais existentes
local_txt_stems = {f.stem for f in TXT_DIR.glob("*.txt")}

# 4. Encontrar as transcrições realmente pendentes
realmente_faltam = [f for f in missing_69 if Path(f).stem not in local_txt_stems]

print("==============================================================")
print("AUDITORIA DO CANAL DA IBPM & PREPARACAO PARA O DESKTOP")
print("==============================================================")
print(f"Total de transcricoes ja no PC: {len(local_txt_stems)} / 455")
print(f"Cultos que ainda FALTAM transcrever: {len(realmente_faltam)}")

for f_name in realmente_faltam:
    print(f"   - {f_name}")

print("\nCopiando/Baixando os audios faltantes para a sua Area de Trabalho...")
for f_name in realmente_faltam:
    stem = Path(f_name).stem
    candidatos = list(AUDIOS_LOCAL_DIR.glob(f"{stem}*"))
    
    if candidatos:
        dest = DESKTOP_DIR / candidatos[0].name
        shutil.copy2(candidatos[0], dest)
        print(f"  [Copiado do PC para o Desktop]: {dest.name}")
    else:
        # Se não estiver no PC, baixa direto do YouTube via yt-dlp
        print(f"  Baixando do YouTube via yt-dlp: {f_name}...")
        m = Path(f_name).name.split("_")[1] if "_" in f_name else ""
        if m:
            url = f"https://www.youtube.com/watch?v={m}"
            out_tmpl = str(DESKTOP_DIR / f"{stem}.%(ext)s")
            subprocess.run(["yt-dlp", "-f", "ba", "-x", "--audio-format", "m4a", "-o", out_tmpl, url], capture_output=True)
            print(f"  [Download do YouTube concluido]: {stem}.m4a")

# 5. Criar arquivo ZIP no Desktop para fácil upload no Kaggle
zip_path = shutil.make_archive(str(DESKTOP_DIR), "zip", str(DESKTOP_DIR))
print("\n==============================================================")
print("TUDO PRONTO NA SUA AREA DE TRABALHO!")
print(f"Pasta: {DESKTOP_DIR}")
print(f"Arquivo ZIP para subir no Kaggle: {zip_path}")
print("==============================================================")
