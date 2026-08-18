import json
import re
import shutil
import subprocess
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"
DESKTOP_DIR = Path(r"C:\Users\matheus\Desktop\audios_faltantes_ibpm")
DESKTOP_DIR.mkdir(parents=True, exist_ok=True)

print("==============================================================")
print("AUDITORIA DEFINITIVA DO CANAL YOUTUBE @ibpmcr7976")
print("==============================================================")

# 1. Escanear aba /videos
print("Escanear aba /videos...")
res_v = subprocess.run(
    ["yt-dlp", "--flat-playlist", "--print", "%(id)s | %(title)s", "https://www.youtube.com/@ibpmcr7976/videos"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
lines_v = [l.strip() for l in res_v.stdout.splitlines() if l.strip()]

# 2. Escanear aba /streams (Lives)
print("Escanear aba /streams (Lives)...")
res_s = subprocess.run(
    ["yt-dlp", "--flat-playlist", "--print", "%(id)s | %(title)s", "https://www.youtube.com/@ibpmcr7976/streams"],
    capture_output=True, text=True, encoding="utf-8", errors="replace"
)
lines_s = [l.strip() for l in res_s.stdout.splitlines() if l.strip()]

all_yt_items = {}
for line in lines_v + lines_s:
    parts = line.split(" | ")
    if len(parts) >= 2:
        all_yt_items[parts[0]] = parts[1]

print(f"\nTotal de videos/lives no YouTube (@ibpmcr7976): {len(all_yt_items)}")

# 3. Mapear os IDs de 11 caracteres dos 451 arquivos no PC
txt_files = list(TXT_DIR.glob("*.txt"))
local_ids = set()

for f in txt_files:
    m = re.search(r'([a-zA-Z0-9_-]{11})', f.stem)
    if m:
        local_ids.add(m.group(1))

print(f"Total de transcricoes ja no seu PC: {len(txt_files)}")
print(f"Total de IDs unicos do YouTube identificados no seu PC: {len(local_ids)}")

# 4. Cruzamento Exato: quais vídeos do YouTube NÃO estão no seu PC?
faltantes = []
for yt_id, title in all_yt_items.items():
    if yt_id not in local_ids:
        faltantes.append({"id": yt_id, "title": title})

print(f"\n==============================================================")
print(f"CULTOS DO YOUTUBE QUE REALMENTE FALTAM NO SEU PC: {len(faltantes)}")
print("==============================================================")

for idx, f in enumerate(faltantes, start=1):
    titulo_limpo = f['title'].encode('ascii', 'ignore').decode('ascii')
    print(f"  {idx:02d}. ID: {f['id']} | Titulo: {titulo_limpo}")

if faltantes:
    print(f"\nBaixando os {len(faltantes)} audios faltantes para a sua Area de Trabalho...")
    for idx, f in enumerate(faltantes, start=1):
        url = f"https://www.youtube.com/watch?v={f['id']}"
        out_tmpl = str(DESKTOP_DIR / f"{idx:03d}_{f['id']}_audio.%(ext)s")
        titulo_limpo = f['title'].encode('ascii', 'ignore').decode('ascii')
        print(f"  [{idx}/{len(faltantes)}] Baixando audio: {titulo_limpo}...")
        subprocess.run(["yt-dlp", "-f", "ba", "-x", "--audio-format", "m4a", "-o", out_tmpl, url], capture_output=True)

    zip_path = shutil.make_archive(str(DESKTOP_DIR), "zip", str(DESKTOP_DIR))
    print(f"\nZIP atualizado na Area de Trabalho: {zip_path}")
else:
    print("\nPARABENS! 100% DE TODOS OS VIDEOS E LIVES DO CANAL JA ESTAO NO SEU COMPUTADOR!")

print("==============================================================")
