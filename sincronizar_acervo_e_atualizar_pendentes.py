"""
sincronizar_acervo_e_atualizar_pendentes.py
=============================================
1. Mapeia todas as transcricoes concluidas por YouTube Video ID (VID).
2. Sincroniza e renomeia identicamente os arquivos de audio (data/audio_podcasts/)
   e as transcricoes (transcricoes_fase2/) com o prefixo sequencial (001_..., 002_..., etc).
3. Varre o acervo geral para identificar quais cultos do canal AINDA NAO possuem transcricao.
4. Gera a lista atualizada e limpa em data/lista_audios_sem_transcricao.txt pronta para o Kaggle!

Uso:
    python sincronizar_acervo_e_atualizar_pendentes.py
"""

import re
import sys
import os
import shutil
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
AUDIO_DIR = BASE_DIR / "data" / "audio_podcasts"
TRANS_DIR = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
INSIGHTS_DIR = BASE_DIR / "data" / "audio_podcasts" / "conteudos_fase3"
LISTA_PENDENTES = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"

def extract_vid(name):
    m = re.search(r'_([a-zA-Z0-9_-]{11})_', str(name))
    return m.group(1) if m else None

def clean_stem(stem):
    return re.sub(r'^\d{3}_', '', stem)

def main():
    print("=" * 70)
    print("🔄 IBPM CR - SINCRONIZAÇÃO DE ACERVO E CRIAÇÃO DE PACOTE KAGGLE")
    print("=" * 70)

    # 1. Obter transcrições completas válidas
    txt_files = sorted([f for f in TRANS_DIR.glob("*.txt") if f.name != "execution_log.txt"])
    print(f"\n📄 Total de transcrições prontas: {len(txt_files)}")

    # Mapear VID -> arquivo de transcrição
    vid_to_txt = {}
    for f in txt_files:
        vid = extract_vid(f.name)
        if vid:
            vid_to_txt[vid] = f

    print(f"🔑 VIDs de transcrições únicas mapeadas: {len(vid_to_txt)}")

    # 2. Re-indexar sequencialmente transcrições e áudios locais por VID
    print("\n📦 Sincronizando e renomeando arquivos por VID (001 a N)...")

    temp_trans = TRANS_DIR / "_temp_sync"
    temp_media = AUDIO_DIR / "_temp_sync"
    temp_insights = INSIGHTS_DIR / "_temp_sync"

    temp_trans.mkdir(exist_ok=True)
    temp_media.mkdir(exist_ok=True)
    temp_insights.mkdir(exist_ok=True)

    vid_to_novo_stem = {}

    for idx, f in enumerate(txt_files, 1):
        stem_limpo = clean_stem(f.stem)
        novo_stem = f"{idx:03d}_{stem_limpo}"
        vid = extract_vid(f.name)

        if vid:
            vid_to_novo_stem[vid] = novo_stem

        # Mover transcrição
        shutil.move(str(f), str(temp_trans / f"{novo_stem}.txt"))

        # Mover insights se existir
        insights_f = INSIGHTS_DIR / f"{f.stem}.insights.json"
        if insights_f.exists():
            shutil.move(str(insights_f), str(temp_insights / f"{novo_stem}.insights.json"))

    # Mover mídias correspondentes por VID
    media_files = [m for m in AUDIO_DIR.iterdir() if m.is_file() and m.suffix in ['.webm', '.mp4', '.m4a', '.mp3']]
    media_sincronizadas = 0

    for m in media_files:
        vid = extract_vid(m.name)
        if vid and vid in vid_to_novo_stem:
            novo_stem = vid_to_novo_stem[vid]
            shutil.move(str(m), str(temp_media / f"{novo_stem}{m.suffix}"))
            media_sincronizadas += 1
        else:
            # Áudio sem transcrição ou não alinhado
            pass

    # Restaurar das pastas temp
    for tmp in temp_trans.glob("*.txt"):
        shutil.move(str(tmp), str(TRANS_DIR / tmp.name))
    temp_trans.rmdir()

    for tmp in temp_insights.glob("*.insights.json"):
        shutil.move(str(tmp), str(INSIGHTS_DIR / tmp.name))
    temp_insights.rmdir()

    for tmp in temp_media.iterdir():
        if tmp.is_file():
            shutil.move(str(tmp), str(AUDIO_DIR / tmp.name))
    temp_media.rmdir()

    print(f"✅ {len(txt_files)} transcrições e {media_sincronizadas} mídias sincronizadas com nomes idênticos!")

    # 3. Atualizar a lista de pendentes para o Kaggle
    print("\n📋 Auditando cultos pendentes para a lista do Kaggle...")

    # Ler lista mestre original se existir
    pendentes_originais = []
    if LISTA_PENDENTES.exists():
        pendentes_originais = [
            l.strip() for l in LISTA_PENDENTES.read_text(encoding='utf-8').split('\n')
            if l.strip() and not l.startswith('#')
        ]

    # Filtrar apenas VIDs que AINDA NÃO possuem transcrição pronta
    novos_pendentes = []
    vids_concluidos = set(vid_to_txt.keys())

    for item in pendentes_originais:
        vid = extract_vid(item)
        if vid and vid not in vids_concluidos:
            novos_pendentes.append(item)

    print(f"📊 Transcrições Concluídas: {len(vids_concluidos)}")
    print(f"⏳ Cultos Faltando Transcrever: {len(novos_pendentes)}")

    # Reescrever lista de pendentes limpa
    with open(LISTA_PENDENTES, "w", encoding="utf-8") as rf:
        rf.write(f"# LISTA ATUALIZADA DE PENDENTES KAGGLE - {datetime.now()}\n")
        rf.write(f"# Total concluidos: {len(vids_concluidos)} | Faltando: {len(novos_pendentes)}\n")
        for item in novos_pendentes:
            rf.write(item + "\n")

    print(f"✅ Arquivo 'data/lista_audios_sem_transcricao.txt' atualizado com {len(novos_pendentes)} pendentes!")

    print("\n" + "🎉" * 20)
    print("SINCRONIZAÇÃO COMPLETA E PRONTA PARA O KAGGLE!")
    print(f"• Transcrições prontas e alinhadas: {len(txt_files)}")
    print(f"• Mídias locais alinhadas: {media_sincronizadas}")
    print(f"• Pendentes para rodar no Kaggle: {len(novos_pendentes)}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
