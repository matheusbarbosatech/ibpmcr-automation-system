import sys
import csv
import re
import subprocess
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
CSV_PATH = BASE_DIR / "dataset_transcricoes" / "streams" / "resumo_playwright.csv"
PASTA_TXT = BASE_DIR / "dataset_transcricoes" / "streams" / "txt"
PASTA_FALSOS = BASE_DIR / "dataset_transcricoes" / "streams" / "falsos_positivos"
PASTA_AUDIOS_LOCAL = BASE_DIR / "dataset_transcricoes" / "audios"
REMOTE_DESTINO = "meudrive:IBPM_CR_Cortes/audio_podcasts"

print(f"📖 Lendo resumo_playwright.csv para calcular a numeração CRONOLÓGICA (001 = mais antigo de 2022)...")

if not CSV_PATH.exists():
    print(f"❌ Arquivo {CSV_PATH} não encontrado!")
    sys.exit(1)

with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    linhas_csv = list(csv.DictReader(f))

total_videos = len(linhas_csv)
print(f"📊 Total de vídeos no catálogo: {total_videos}")

# Mapa de ID -> Nome Base Descritivo (sem prefixo numérico antigo)
mapa_id_descricao = {}
for p_dir in [PASTA_TXT, PASTA_FALSOS]:
    if p_dir.exists():
        for arq in p_dir.glob("*.txt"):
            partes = arq.stem.split("_")
            if len(partes) >= 2:
                vid_id = partes[1]
                # Pega toda a descrição após o id
                descricao = "_".join(partes[2:])
                mapa_id_descricao[vid_id] = (partes[0], vid_id, descricao, arq.stem)

# Mapa de ID -> Nome Cronológico Oficial (ex: 001_2hvx5L2DR2U_culto_santa_ceia...)
mapa_id_cronologico = {}

for row in linhas_csv:
    csv_idx = int(row['index'])
    vid_id = row['id']
    
    # Numeração Cronológica: 001 para o mais antigo (linha 455), 455 para o mais recente (linha 1)
    cron_idx = (total_videos - csv_idx + 1)
    prefixo_cron = f"{cron_idx:03d}"
    
    if vid_id in mapa_id_descricao:
        _, _, desc, _ = mapa_id_descricao[vid_id]
        if desc:
            nome_cron = f"{prefixo_cron}_{vid_id}_{desc}"
        else:
            nome_cron = f"{prefixo_cron}_{vid_id}"
    else:
        # Sanitizar título do CSV se não estiver na pasta local
        titulo_clean = re.sub(r'[^a-zA-Z0-9_]', '_', row.get('title', '')).strip('_')
        nome_cron = f"{prefixo_cron}_{vid_id}_{titulo_clean}"
        
    mapa_id_cronologico[vid_id] = nome_cron

print("Exemplos da Nova Numeração Cronológica:")
print("  • 001 (Mais Antigo de 2022):", mapa_id_cronologico[linhas_csv[-1]['id']])
print("  • 455 (Mais Recente de 2026):", mapa_id_cronologico[linhas_csv[0]['id']])

# -------------------------------------------------------------
# 1. Renomear arquivos locais em dataset_transcricoes/audios
# -------------------------------------------------------------
if PASTA_AUDIOS_LOCAL.exists():
    print(f"\n📂 Padronizando arquivos locais em dataset_transcricoes/audios...")
    for arq_local in list(PASTA_AUDIOS_LOCAL.glob("*.*")):
        suffix = arq_local.suffix
        for vid_id, nome_cron in mapa_id_cronologico.items():
            if vid_id in arq_local.name:
                novo_nome_local = PASTA_AUDIOS_LOCAL / f"{nome_cron}{suffix}"
                if arq_local != novo_nome_local and not novo_nome_local.exists():
                    print(f"  Local DE:   {arq_local.name}")
                    print(f"        PARA: {novo_nome_local.name}")
                    arq_local.rename(novo_nome_local)

# -------------------------------------------------------------
# 2. Renomear arquivos no Google Drive via rclone moveto
# -------------------------------------------------------------
print(f"\n📡 Listando arquivos da pasta do Google Drive: {REMOTE_DESTINO}...")
res = subprocess.run(["rclone", "lsf", REMOTE_DESTINO], capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0:
    print(f"❌ Erro ao listar Drive: {res.stderr}")
    sys.exit(1)

arquivos_drive = [f.strip() for f in res.stdout.splitlines() if f.strip()]
print(f"📁 Encontrados {len(arquivos_drive)} arquivos no Drive.")

renomear_plan = []
for f_drive in arquivos_drive:
    ext = Path(f_drive).suffix
    for vid_id, nome_cron in mapa_id_cronologico.items():
        if vid_id in f_drive:
            nome_desejado = f"{nome_cron}{ext}"
            if f_drive != nome_desejado:
                renomear_plan.append((f_drive, nome_desejado))
            break

print(f"\n🔄 Total de arquivos que precisam ser ajustados no Drive: {len(renomear_plan)}")

if renomear_plan:
    print("🚀 Executando renomeação cronológica no Google Drive (rclone moveto)...")
    sucessos = 0
    erros = 0
    for idx, (de, para) in enumerate(renomear_plan, start=1):
        caminho_de = f"{REMOTE_DESTINO}/{de}"
        caminho_para = f"{REMOTE_DESTINO}/{para}"
        
        print(f"[{idx}/{len(renomear_plan)}] Renomeando no Drive:")
        print(f"   DE:   {de}")
        print(f"   PARA: {para}")
        
        cmd = ["rclone", "moveto", caminho_de, caminho_para]
        res_m = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res_m.returncode == 0:
            sucessos += 1
        else:
            print(f"   ❌ Erro ao renomear {de}: {res_m.stderr.strip()}")
            erros += 1

    print(f"\n🎉 CONCLUSÃO DA PADRONIZAÇÃO CRONOLÓGICA NO DRIVE!")
    print(f"   • Sucessos: {sucessos}")
    print(f"   • Erros:    {erros}")
else:
    print("🎉 Todos os arquivos no Drive já estão na ordem cronológica desejada (001 = 2022 ... 455 = 2026)!")
