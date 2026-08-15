"""
filtrar_e_renomear_cultos_completos.py
======================================
Filtra e limpa a base de dados do IBPM CR:
1. Analisa a duracao real de cada transcricao no acervo.
2. Identifica e exclui arquivos de audio/transcricao curtos (< MIN_MINUTES, padrao: 20 min)
   que nao sao cultos completos (ex: avisos, vinhetas, recortes, lives de teste).
3. Renomeia sequencialmente todos os cultos validos mantidos (001_..., 002_..., 003_...)
   sincronizando transcricoes, arquivos de insights e acervo.

Uso:
    python filtrar_e_renomear_cultos_completos.py --dry-run
    python filtrar_e_renomear_cultos_completos.py --execute --min-minutes 20
"""

import re
import sys
import os
import shutil
import argparse
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
TRANS_DIR = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
INSIGHTS_DIR = BASE_DIR / "data" / "audio_podcasts" / "conteudos_fase3"
AUDIOS_DIR = BASE_DIR / "data" / "audio_podcasts"
LISTA_PENDENTES = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"
RELATORIO_CSV = BASE_DIR / "data" / "relatorio_cortes.csv"
RELATORIO_FILTRO = BASE_DIR / "data" / "relatorio_filtragem_cultos.txt"

parser = argparse.ArgumentParser(description="Filtrar e renomear cultos completos IBPM CR")
parser.add_argument("--execute", action="store_true", help="Executa as exclusoes e renomeacoes")
parser.add_argument("--dry-run", action="store_true", help="Apenas simula a filtragem (padrao se --execute nao for passado)")
parser.add_argument("--min-minutes", type=float, default=20.0, help="Duracao minima em minutos para ser considerado culto completo (padrao: 20.0)")

args = parser.parse_args()
EXECUTE = args.execute and not args.dry_run
MIN_MINUTES = args.min_minutes
MIN_SECONDS = MIN_MINUTES * 60.0

def get_duration_seconds(txt_path):
    """Calcula a duracao real em segundos lendo os timestamps [HH:MM:SS] da transcricao."""
    try:
        content = txt_path.read_text(encoding='utf-8', errors='ignore')
        matches = re.findall(r'\[(\d{2}):(\d{2}):(\d{2})\]', content)
        if not matches:
            return 0.0
        last = matches[-1]
        return float(int(last[0])*3600 + int(last[1])*60 + int(last[2]))
    except Exception:
        return 0.0

def extract_vid(name):
    m = re.search(r'_([a-zA-Z0-9_-]{11})_', str(name))
    return m.group(1) if m else None

def clean_stem(stem):
    """Remove o prefixo numerico antigo tipo '001_' ou '049_' se existir."""
    return re.sub(r'^\d{3}_', '', stem)

def main():
    print("=" * 70)
    print("🧹 IBPM CR - FILTRAGEM E RENOMEAÇÃO DE CULTOS COMPLETOS")
    print(f"   Duração mínima exigida: {MIN_MINUTES:.1f} minutos ({int(MIN_SECONDS)} segundos)")
    if EXECUTE:
        print("   MODO: EXECUTAR (excluirá não-cultos e renomeará a base)")
    else:
        print("   MODO: SIMULAÇÃO / DRY-RUN (nenhum arquivo será alterado)")
    print("=" * 70)

    txt_files = sorted([f for f in TRANS_DIR.glob("*.txt") if f.name != "execution_log.txt"])
    print(f"\n📂 Total de transcrições encontradas: {len(txt_files)}")

    cultos_validos = []
    nao_cultos = []

    for f in txt_files:
        dur_sec = get_duration_seconds(f)
        dur_min = dur_sec / 60.0
        if dur_sec >= MIN_SECONDS:
            cultos_validos.append((f, dur_sec, dur_min))
        else:
            nao_cultos.append((f, dur_sec, dur_min))

    print(f"\n📊 RESUMO DA VARREDURA:")
    print(f"  ✅ Cultos Completos (>= {MIN_MINUTES:.0f} min): {len(cultos_validos)}")
    print(f"  ❌ Não-Cultos / Curtos (< {MIN_MINUTES:.0f} min):  {len(nao_cultos)}")

    if nao_cultos:
        print(f"\n❌ ARQUIVOS IDENTIFICADOS PARA EXCLUSÃO (< {MIN_MINUTES:.0f} min):")
        for f, dur_sec, dur_min in nao_cultos:
            print(f"   • [{dur_min:5.1f} min] {f.name}")

    # Salvar relatório descritivo
    with open(RELATORIO_FILTRO, "w", encoding="utf-8") as rf:
        rf.write(f"RELATÓRIO DE FILTRAGEM DE CULTOS IBPM CR - {datetime.now()}\n")
        rf.write(f"Duração mínima: {MIN_MINUTES} minutos\n")
        rf.write(f"Cultos Válidos: {len(cultos_validos)}\n")
        rf.write(f"Excluídos: {len(nao_cultos)}\n\n")
        rf.write("--- EXCLUÍDOS (< MIN_MINUTES) ---\n")
        for f, dur_sec, dur_min in nao_cultos:
            rf.write(f"[{dur_min:5.1f} min] {f.name}\n")

    if not EXECUTE:
        print(f"\n📋 PLANO DE RENOMEAÇÃO (SIMULAÇÃO):")
        print(f"  Os {len(cultos_validos)} cultos válidos serão renomeados de 001 a {len(cultos_validos):03d}:")
        for idx, (f, dur_sec, dur_min) in enumerate(cultos_validos[:10], 1):
            stem_limpo = clean_stem(f.stem)
            novo_nome = f"{idx:03d}_{stem_limpo}.txt"
            print(f"   [{idx:03d}] {f.name}  ➔  {novo_nome}")
        if len(cultos_validos) > 10:
            print(f"   ... e mais {len(cultos_validos) - 10} cultos.")
        print(f"\n⚠️ Para aplicar as alterações de verdade, rode:")
        print(f"   python filtrar_e_renomear_cultos_completos.py --execute --min-minutes {MIN_MINUTES:.0f}")
        return

    # ─────────────────────────────────────────────────────────────
    # EXECUÇÃO REAL
    # ─────────────────────────────────────────────────────────────
    print(f"\n🚀 EXECUTANDO EXCLUSÕES E RENOMEAÇÃO DA BASE...")

    # 1. Excluir arquivos de transcrição, insights e áudio dos não-cultos
    print("\n1. Deletando não-cultos (< MIN_MINUTES)...")
    for f, dur_sec, dur_min in nao_cultos:
        # Remover transcrição .txt
        f.unlink(missing_ok=True)
        # Remover insights .json
        insights_json = INSIGHTS_DIR / f"{f.stem}.insights.json"
        insights_json.unlink(missing_ok=True)
        # Remover áudio/vídeo se existir em AUDIOS_DIR
        for ext in ['.webm', '.mp3', '.m4a', '.mp4']:
            media_f = AUDIOS_DIR / f"{f.stem}{ext}"
            media_f.unlink(missing_ok=True)
        print(f"   [DELETADO] {f.name} ({dur_min:.1f} min)")

    # 2. Renomear sequencialmente os cultos válidos e sincronizar mídias em AUDIOS_DIR
    print(f"\n2. Renomeando {len(cultos_validos)} cultos válidos de 001 a {len(cultos_validos):03d}...")

    # Mapeamento VID -> Novo Nome para mídias
    vid_to_new_name = {}

    temp_trans = TRANS_DIR / "_temp_renaming"
    temp_insights = INSIGHTS_DIR / "_temp_renaming"
    temp_media = AUDIOS_DIR / "_temp_renaming"
    temp_trans.mkdir(exist_ok=True)
    temp_insights.mkdir(exist_ok=True)
    temp_media.mkdir(exist_ok=True)

    novas_transcricoes = []

    for idx, (f, dur_sec, dur_min) in enumerate(cultos_validos, 1):
        stem_limpo = clean_stem(f.stem)
        novo_stem = f"{idx:03d}_{stem_limpo}"
        novo_txt_name = f"{novo_stem}.txt"

        vid = extract_vid(f.stem)
        if vid:
            vid_to_new_name[vid] = novo_stem

        # Mover transcricao para pasta temp com novo nome
        novo_txt_temp = temp_trans / novo_txt_name
        shutil.move(str(f), str(novo_txt_temp))

        # Mover insights se existir
        old_insights = INSIGHTS_DIR / f"{f.stem}.insights.json"
        if old_insights.exists():
            novo_insights_temp = temp_insights / f"{novo_stem}.insights.json"
            shutil.move(str(old_insights), str(novo_insights_temp))

        novas_transcricoes.append(novo_txt_name)

    # Processar mídias em AUDIOS_DIR (.webm, .m4a, .mp3, .mp4)
    media_files = [m for m in AUDIOS_DIR.iterdir() if m.is_file() and m.suffix in ['.webm', '.m4a', '.mp3', '.mp4']]
    media_renomeadas = 0
    media_deletadas = 0

    for m in media_files:
        vid = extract_vid(m.name)
        if vid and vid in vid_to_new_name:
            target_name = f"{vid_to_new_name[vid]}{m.suffix}"
            shutil.move(str(m), str(temp_media / target_name))
            media_renomeadas += 1
        else:
            m.unlink()
            media_deletadas += 1

    # Mover de volta da pasta temp para a pasta principal
    for tmp_f in temp_trans.glob("*.txt"):
        shutil.move(str(tmp_f), str(TRANS_DIR / tmp_f.name))
    temp_trans.rmdir()

    for tmp_f in temp_insights.glob("*.insights.json"):
        shutil.move(str(tmp_f), str(INSIGHTS_DIR / tmp_f.name))
    temp_insights.rmdir()

    for tmp_f in temp_media.iterdir():
        if tmp_f.is_file():
            shutil.move(str(tmp_f), str(AUDIOS_DIR / tmp_f.name))
    temp_media.rmdir()

    print(f"✅ Renomeação concluída! {len(novas_transcricoes)} transcrições e {media_renomeadas} mídias organizadas (001 a {len(novas_transcricoes):03d}).")
    print(f"🗑️  {media_deletadas} mídias não-culto excluídas de data/audio_podcasts/.")

    # 3. Limpar relatorio_cortes.csv para forçar regeneração na Fase 3 v2
    if RELATORIO_CSV.exists():
        RELATORIO_CSV.unlink()
        print("✅ relatorio_cortes.csv removido para forçar regeneração limpa na Fase 3.")

    print("\n" + "🎉" * 20)
    print("ACERVO REORGANIZADO E LIMPO COM SUCESSO!")
    print(f"• {len(nao_cultos)} arquivos curtos removidos")
    print(f"• {len(cultos_validos)} cultos completos indexados (001_{clean_stem(cultos_validos[0][0].stem)} até {len(cultos_validos):03d}_...)")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
