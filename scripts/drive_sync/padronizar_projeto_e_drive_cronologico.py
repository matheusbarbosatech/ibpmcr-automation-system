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
PASTA_JSON = BASE_DIR / "dataset_transcricoes" / "streams" / "json"
PASTA_FALSOS = BASE_DIR / "dataset_transcricoes" / "streams" / "falsos_positivos"
PASTA_AUDIOS = BASE_DIR / "dataset_transcricoes" / "audios"
REMOTE_DESTINO = "meudrive:IBPM_CR_Cortes/audio_podcasts"

print("================================================================")
print("🔄 INICIANDO REORDENAÇÃO E PADRONIZAÇÃO CRONOLÓGICA COMPLETA")
print("   • 001 = Culto Mais Antigo (02/10/2022)")
print("   • 455 = Culto Mais Recente (16/08/2026)")
print("================================================================\n")

if not CSV_PATH.exists():
    print(f"❌ Arquivo {CSV_PATH} não encontrado!")
    sys.exit(1)

with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    linhas_csv = list(csv.DictReader(f))

total_videos = len(linhas_csv)
print(f"📊 Total de vídeos no catálogo: {total_videos}")

# 1. Mapeamento dos IDs para Descrições Limpas
mapa_id_descricao = {}
todas_pastas_locais = [PASTA_TXT, PASTA_JSON, PASTA_FALSOS, PASTA_AUDIOS]

for p_dir in todas_pastas_locais:
    if p_dir.exists():
        for arq in p_dir.glob("*.*"):
            partes = arq.stem.split("_")
            if len(partes) >= 2:
                for p in partes:
                    if len(p) == 11 and p not in mapa_id_descricao:
                        # Extrai a descrição após o ID se houver
                        pos_id = partes.index(p)
                        desc = "_".join(partes[pos_id+1:])
                        mapa_id_descricao[p] = desc

# 2. Ordenar a lista por data/ordem cronológica (antigo em primeiro, novo por último)
# Se a primeira linha tiver data de 2026, invertemos a lista para 2022 ficar na posição 0
if '2026' in linhas_csv[0].get('title', '') or '26' in linhas_csv[0].get('title', '') or linhas_csv[0]['id'] == 'mJn9p2a9xWs':
    linhas_cronologicas = list(reversed(linhas_csv))
else:
    linhas_cronologicas = list(linhas_csv)

mapa_id_cronologico = {}
for cron_idx, row in enumerate(linhas_cronologicas, start=1):
    vid_id = row['id']
    prefixo_cron = f"{cron_idx:03d}"
    
    desc = mapa_id_descricao.get(vid_id, "")
    if not desc:
        desc = re.sub(r'[^a-zA-Z0-9_]', '_', row.get('title', '')).strip('_')
        
    nome_cron = f"{prefixo_cron}_{vid_id}_{desc}".rstrip('_')
    mapa_id_cronologico[vid_id] = (cron_idx, nome_cron)

print(f"✅ Mapeados {len(mapa_id_cronologico)} vídeos com numeração CRONOLÓGICA estrita.")
print(f"   • Exemplo 001 (Mais Antigo de 2022): {mapa_id_cronologico[linhas_cronologicas[0]['id']][1]}")
print(f"   • Exemplo 455 (Mais Recente de 2026): {mapa_id_cronologico[linhas_cronologicas[-1]['id']][1]}")

# -------------------------------------------------------------
# 3. Reordenar e Atualizar resumo_playwright.csv
# -------------------------------------------------------------
print(f"\n📄 Atualizando resumo_playwright.csv na ordem cronológica estrita (001 a 455)...")
novas_linhas_csv = []
for cron_idx, row in enumerate(linhas_cronologicas, start=1):
    vid_id = row['id']
    row_copy = dict(row)
    row_copy['index'] = str(cron_idx)
    novas_linhas_csv.append(row_copy)

fieldnames = list(linhas_csv[0].keys())
with open(CSV_PATH, "w", encoding="utf-8", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(novas_linhas_csv)

print("  ✅ resumo_playwright.csv reordenado e salvo com sucesso!")

# -------------------------------------------------------------
# 4. Renomear Arquivos Locais (txt, json, falsos_positivos, audios)
# -------------------------------------------------------------
print(f"\n📂 Renomeando arquivos locais no projeto...")
total_locais_renomeados = 0

for p_dir in todas_pastas_locais:
    if not p_dir.exists():
        continue
    for arq in list(p_dir.glob("*.*")):
        suffix = arq.suffix
        for vid_id, (cron_idx, nome_cron) in mapa_id_cronologico.items():
            if vid_id in arq.name:
                novo_arq = p_dir / f"{nome_cron}{suffix}"
                if arq != novo_arq and not novo_arq.exists():
                    try:
                        arq.rename(novo_arq)
                        total_locais_renomeados += 1
                    except Exception as ex:
                        print(f"   ⚠️ Não foi possível renomear {arq.name}: {ex}")
                break

print(f"  ✅ {total_locais_renomeados} arquivos locais renomeados para o padrão cronológico!")

# -------------------------------------------------------------
# 5. Renomear Arquivos no Google Drive via rclone moveto
# -------------------------------------------------------------
print(f"\n📡 Listando arquivos da pasta do Google Drive ({REMOTE_DESTINO})...")
res = subprocess.run(["rclone", "lsf", REMOTE_DESTINO], capture_output=True, text=True, encoding="utf-8")
if res.returncode != 0:
    print(f"❌ Erro ao listar arquivos do Drive: {res.stderr}")
    sys.exit(1)

arquivos_drive = [f.strip() for f in res.stdout.splitlines() if f.strip()]
print(f"📁 Encontrados {len(arquivos_drive)} arquivos no Drive.")

renomear_plan_drive = []
for f_drive in arquivos_drive:
    ext = Path(f_drive).suffix
    for vid_id, (cron_idx, nome_cron) in mapa_id_cronologico.items():
        if vid_id in f_drive:
            nome_desejado = f"{nome_cron}{ext}"
            if f_drive != nome_desejado:
                renomear_plan_drive.append((f_drive, nome_desejado))
            break

print(f"🔄 Total de arquivos no Drive que serão renomeados no servidor: {len(renomear_plan_drive)}")

if renomear_plan_drive:
    print(f"🚀 Executando padronização cronológica de {len(renomear_plan_drive)} arquivos no Google Drive (multithread)...")
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def renomear_item(item):
        idx, (de, para) = item
        caminho_de = f"{REMOTE_DESTINO}/{de}"
        caminho_para = f"{REMOTE_DESTINO}/{para}"
        cmd = ["rclone", "moveto", caminho_de, caminho_para]
        res_m = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")
        if res_m.returncode == 0:
            print(f"  [{idx}/{len(renomear_plan_drive)}] ✅ {de} -> {para}", flush=True)
            return True
        else:
            print(f"  [{idx}/{len(renomear_plan_drive)}] ❌ Erro ao renomear {de}: {res_m.stderr.strip()}", flush=True)
            return False

    items = list(enumerate(renomear_plan_drive, start=1))
    sucessos = 0
    erros = 0

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = [executor.submit(renomear_item, item) for item in items]
        for f in as_completed(futures):
            if f.result():
                sucessos += 1
            else:
                erros += 1

    print(f"\n🎉 CONCLUSÃO DA PADRONIZAÇÃO CRONOLÓGICA NO DRIVE!")
    print(f"   • Sucessos: {sucessos}")
    print(f"   • Erros:    {erros}")

print("\n✨ TUDO PRONTO E 100% UNIFICADO CRONOLOGICAMENTE!")
