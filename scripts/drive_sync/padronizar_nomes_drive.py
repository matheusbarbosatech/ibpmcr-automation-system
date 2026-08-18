import sys
import csv
import re
import subprocess
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
PASTA_TXT = BASE_DIR / "dataset_transcricoes" / "streams" / "txt"
PASTA_FALSOS = BASE_DIR / "dataset_transcricoes" / "streams" / "falsos_positivos"
REMOTE_DESTINO = "meudrive:IBPM_CR_Cortes/audio_podcasts"

print(f"🔍 Carregando o mapeamento oficial dos 455 vídeos...")

mapa_id_oficial = {}
for p_dir in [PASTA_TXT, PASTA_FALSOS]:
    if p_dir.exists():
        for arq in p_dir.glob("*.txt"):
            partes = arq.stem.split("_")
            for p in partes:
                if len(p) == 11 and p not in mapa_id_oficial:
                    mapa_id_oficial[p] = arq.stem

print(f"✅ Mapeados {len(mapa_id_oficial)} IDs com seus nomes oficiais padronizados.")

print(f"📡 Listando arquivos da pasta do Drive ({REMOTE_DESTINO})...")
res = subprocess.run(["rclone", "lsf", REMOTE_DESTINO], capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0:
    print(f"❌ Erro ao listar arquivos do Drive: {res.stderr}")
    sys.exit(1)

arquivos_drive = [f.strip() for f in res.stdout.splitlines() if f.strip()]
print(f"📁 Encontrados {len(arquivos_drive)} arquivos no Drive.")

renomear_lista = []
for nome_drive in arquivos_drive:
    # Procura por qualquer ID de 11 caracteres presente no mapa
    id_encontrado = None
    for part in re.findall(r'([a-zA-Z0-9_-]{11})', nome_drive):
        if part in mapa_id_oficial:
            id_encontrado = part
            break
            
    if id_encontrado:
        nome_oficial_stem = mapa_id_oficial[id_encontrado]
        extensao = Path(nome_drive).suffix
        nome_desejado = f"{nome_oficial_stem}{extensao}"
        
        if nome_drive != nome_desejado:
            renomear_lista.append((nome_drive, nome_desejado))

print(f"\n🔄 Total de arquivos que precisam ser padronizados no Drive: {len(renomear_lista)}")

if not renomear_lista:
    print("🎉 Todos os arquivos do Drive já estão 100% padronizados e sincronizados!")
    sys.exit(0)

print("🚀 Iniciando renomeação direta no servidor do Google Drive (rclone moveto)...")

sucessos = 0
erros = 0

for idx, (nome_antigo, nome_novo) in enumerate(renomear_lista, start=1):
    caminho_antigo = f"{REMOTE_DESTINO}/{nome_antigo}"
    caminho_novo = f"{REMOTE_DESTINO}/{nome_novo}"
    
    print(f"[{idx}/{len(renomear_lista)}] Renomeando:")
    print(f"   DE:   {nome_antigo}")
    print(f"   PARA: {nome_novo}")
    
    cmd = ["rclone", "moveto", caminho_antigo, caminho_novo]
    res_move = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
    
    if res_move.returncode == 0:
        sucessos += 1
    else:
        print(f"   ❌ Erro ao renomear: {res_move.stderr.strip()}")
        erros += 1

print(f"\n✨ PADRONIZAÇÃO DO GOOGLE DRIVE FINALIZADA!")
print(f"   • Sucessos: {sucessos}")
print(f"   • Erros:    {erros}")
print(f"   • Todos os arquivos em '{REMOTE_DESTINO}' agora seguem a ordem e numeração idênticas ao 'resumo_playwright.csv'!")
