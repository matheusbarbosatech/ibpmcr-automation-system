from src.padronizar_projeto_e_drive_cronologico import total_locais_renomeados
import sys
import csv
import re
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
DATASET_DIR = BASE_DIR / "dataset_transcricoes"
CSV_PATH = DATASET_DIR / "streams" / "resumo_playwright.csv"

print("================================================================")
print("📂 PADRONIZANDO PASTA LOCAL: dataset_transcricoes")
print("================================================================\n")

if not CSV_PATH.exists():
    print(f"❌ Arquivo {CSV_PATH} não encontrado!")
    sys.exit(1)

with open(CSV_PATH, "r", encoding="utf-8-sig") as f:
    linhas_csv = list(csv.DictReader(f))

# Mapear ID do vídeo -> Numeração Cronológica (ex: 001 para o mais antigo de 2022, 455 para o mais novo de 2026)
mapa_cron = {}
for row in linhas_csv:
    idx = int(row['index'])
    vid_id = row['id']
    prefixo = f"{idx:03d}"
    mapa_cron[vid_id] = (idx, prefixo)

print(f"📊 Carregados {len(mapa_cron)} mapeamentos do resumo_playwright.csv.")

pastas_para_padronizar = [
    DATASET_DIR / "streams" / "txt",
    DATASET_DIR / "streams" / "json",
    DATASET_DIR / "streams" / "falsos_positivos",
    DATASET_DIR / "audios"
]

total_renomeados = 0

for p_dir in pastas_para_padronizar:
    if not p_dir.exists():
        continue
    
    print(f"\n🔍 Processando pasta: {p_dir.relative_to(BASE_DIR)}...")
    arquivos = list(p_dir.glob("*.*"))
    renomeados_pasta = 0
    
    for arq in arquivos:
        suffix = arq.suffix
        stem = arq.stem
        
        # Encontrar qual ID do vídeo está neste arquivo
        id_encontrado = None
        for vid_id in mapa_cron:
            if vid_id in stem:
                id_encontrado = vid_id
                break
                
        if id_encontrado:
            idx, prefixo = mapa_cron[id_encontrado]
            
            # Se o arquivo já começa com o prefixo correto, pula
            if stem.startswith(f"{prefixo}_"):
                continue
                
            # Extrair a descrição mantendo o nome bonito
            partes = stem.split("_")
            pos_id = partes.index(id_encontrado) if id_encontrado in partes else -1
            
            if pos_id != -1 and pos_id + 1 < len(partes):
                desc = "_".join(partes[pos_id+1:])
                novo_stem = f"{prefixo}_{id_encontrado}_{desc}"
            else:
                novo_stem = f"{prefixo}_{id_encontrado}"
                
            novo_caminho = p_dir / f"{novo_stem}{suffix}"
            
            if arq != novo_caminho and not novo_caminho.exists():
                try:
                    arq.rename(novo_caminho)
                    renomeados_pasta += 1
                    total_renomeados += 1
                except Exception as ex:
                    print(f"   ⚠️ Erro ao renomear {arq.name}: {ex}")
                    
    print(f"   • {renomeados_pasta} arquivos renomeados nesta pasta.")

print(f"\n✨ PADRONIZAÇÃO LOCAL CONCLUÍDA! Total de {total_locais_renomeados if 'total_locais_renomeados' in locals() else total_renomeados} arquivos padronizados.")
