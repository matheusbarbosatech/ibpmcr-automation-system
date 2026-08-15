"""
remover_conteudo_sem_pregacao.py
===============================
Identifica e remove arquivos que NÃO contém pregação ou ensino bíblico expositivo
(ex: apenas oração contínua, momento de intercessão puro, louvor puro, sala de adoração).

Critérios de Detecção de Não-Pregação:
  1. Títulos/arquivos indicando "sala de adoração", "oração", "intercessão", "ensaio", "boletim".
  2. Densidade de Exposição Bíblica nula ou baixíssima (pouquíssimos termos como bíblia, versículo, capítulo, mensagem, ensino).
  3. Proporção desproporcional de repetição de oração contínua vs pregação.

Uso:
    python remover_conteudo_sem_pregacao.py --dry-run
    python remover_conteudo_sem_pregacao.py --execute
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
RELATORIO_CSV = BASE_DIR / "data" / "relatorio_cortes.csv"
RELATORIO_SAIDA = BASE_DIR / "data" / "relatorio_remocao_sem_pregacao.txt"

parser = argparse.ArgumentParser(description="Remover áudios/transcrições sem pregação bíblica")
parser.add_argument("--execute", action="store_true", help="Executa as exclusões e a renomeação")
parser.add_argument("--dry-run", action="store_true", help="Apenas simula a detecção e exibe o relatório")
args = parser.parse_args()

EXECUTE = args.execute and not args.dry_run

PREACHING_KEYWORDS = [
    r'b[íi]blia', r'cap[íi]tulo', r'vers[íi]culo', r'livro de', r'leitura',
    r'palavra de deus', r'mensagem', r'ensino', r'primeiro ponto', r'segundo ponto',
    r'terceiro ponto', r'li[çc][ãa]o', r'explica[çc][ãa]o', r'significa',
    r'exegese', r'prega[çc][ãa]o', r'evangelho de', r'carta de', r'paulo escreve',
    r'jesus disse', r'deus fala', r'texto base', r'abram em'
]

PRAYER_KEYWORDS = [
    r'vamos orar', r'pode orar', r'oremos', r'senhor meu deus',
    r'te louvamos', r'te adoramos', r'gl[óo]ria a deus', r'aleluia'
]

TITLE_EXCLUDE_PATTERNS = [
    r'sala_de_adora', r'ensaio', r'intercessao', r'boletim', r'reuniao_de_obreiros'
]

def extract_vid(name):
    m = re.search(r'_([a-zA-Z0-9_-]{11})_', str(name))
    return m.group(1) if m else None

def clean_stem(stem):
    return re.sub(r'^\d{3}_', '', stem)

def main():
    print("=" * 70)
    print("🔍 IBPM CR - FILTRAGEM DE CONTEÚDO SEM PREGAÇÃO / ENSINO BÍBLICO")
    if EXECUTE:
        print("   MODO: EXECUTAR (removerá não-pregações e renomeará a base)")
    else:
        print("   MODO: SIMULAÇÃO / DRY-RUN (nenhum arquivo será alterado)")
    print("=" * 70)

    txt_files = sorted([f for f in TRANS_DIR.glob("*.txt") if f.name != "execution_log.txt"])
    print(f"\n📂 Analisando {len(txt_files)} transcrições...")

    pregacoes_validas = []
    sem_pregacao = []

    for f in txt_files:
        content = f.read_text(encoding='utf-8', errors='ignore')
        content_lower = content.lower()
        
        preach_hits = sum(len(re.findall(p, content_lower)) for p in PREACHING_KEYWORDS)
        prayer_hits = sum(len(re.findall(p, content_lower)) for p in PRAYER_KEYWORDS)
        words = re.findall(r'\b\w+\b', content_lower)
        total_w = len(words)

        is_title_match = any(re.search(p, f.name.lower()) for p in TITLE_EXCLUDE_PATTERNS)
        is_low_preach = preach_hits < 10
        is_prayer_dominated = (preach_hits < 15 and prayer_hits > preach_hits * 3)

        if is_title_match or is_low_preach or is_prayer_dominated:
            reason = []
            if is_title_match: reason.append("Título de oração/louvor/ensaio")
            if is_low_preach: reason.append(f"Pouca pregação ({preach_hits} menções)")
            if is_prayer_dominated: reason.append(f"Oração dominante ({prayer_hits} oração vs {preach_hits} pregação)")
            sem_pregacao.append((f, preach_hits, prayer_hits, total_w, " + ".join(reason)))
        else:
            pregacoes_validas.append((f, preach_hits, prayer_hits, total_w))

    print(f"\n📊 RESULTADO DA ANALISE COGNITIVA:")
    print(f"  ✅ Pregações / Ensinamentos Válidos: {len(pregacoes_validas)}")
    print(f"  ❌ Arquivos sem Pregação (Apenas Oração/Louvor/Outros): {len(sem_pregacao)}")

    if sem_pregacao:
        print(f"\n❌ LISTA DE ARQUIVOS IDENTIFICADOS PARA EXCLUSÃO (SEM PREGAÇÃO):")
        for f, p_hits, pr_hits, tot_w, motivo in sem_pregacao[:30]:
            print(f"   • [{motivo}] {f.name}")
        if len(sem_pregacao) > 30:
            print(f"   ... e mais {len(sem_pregacao) - 30} arquivos.")

    with open(RELATORIO_SAIDA, "w", encoding="utf-8") as rf:
        rf.write(f"RELATÓRIO DE REMOÇÃO DE CONTEÚDO SEM PREGAÇÃO - {datetime.now()}\n")
        rf.write(f"Pregações Mantidas: {len(pregacoes_validas)}\n")
        rf.write(f"Removidos: {len(sem_pregacao)}\n\n")
        for f, p_hits, pr_hits, tot_w, motivo in sem_pregacao:
            rf.write(f"[{motivo}] {f.name}\n")

    print(f"\n📄 Relatório detalhado salvo em: {RELATORIO_SAIDA}")

    if not EXECUTE:
        print(f"\n⚠️ Para executar a remoção e reorganização sequencial (001 a {len(pregacoes_validas):03d}), rode:")
        print(f"   python remover_conteudo_sem_pregacao.py --execute")
        return

    # ─────────────────────────────────────────────────────────────
    # EXECUÇÃO REAL
    # ─────────────────────────────────────────────────────────────
    print(f"\n🚀 EXECUTANDO EXCLUSÕES E RENOMEAÇÃO SEQUENCIAL DOS CULTOS VÁLIDOS...")

    # 1. Deletar arquivos sem pregação
    for f, p_hits, pr_hits, tot_w, motivo in sem_pregacao:
        f.unlink(missing_ok=True)
        insights_f = INSIGHTS_DIR / f"{f.stem}.insights.json"
        insights_f.unlink(missing_ok=True)
        for ext in ['.webm', '.m4a', '.mp3', '.mp4']:
            media_f = AUDIOS_DIR / f"{f.stem}{ext}"
            media_f.unlink(missing_ok=True)

    # 2. Renomear sequencialmente as pregações válidas (001 a N)
    vid_to_new_name = {}
    temp_trans = TRANS_DIR / "_temp_renaming"
    temp_insights = INSIGHTS_DIR / "_temp_renaming"
    temp_media = AUDIOS_DIR / "_temp_renaming"
    temp_trans.mkdir(exist_ok=True)
    temp_insights.mkdir(exist_ok=True)
    temp_media.mkdir(exist_ok=True)

    novas_transcricoes = []

    for idx, (f, p_hits, pr_hits, tot_w) in enumerate(pregacoes_validas, 1):
        stem_limpo = clean_stem(f.stem)
        novo_stem = f"{idx:03d}_{stem_limpo}"
        novo_txt_name = f"{novo_stem}.txt"

        vid = extract_vid(f.stem)
        if vid:
            vid_to_new_name[vid] = novo_stem

        shutil.move(str(f), str(temp_trans / novo_txt_name))

        old_insights = INSIGHTS_DIR / f"{f.stem}.insights.json"
        if old_insights.exists():
            shutil.move(str(old_insights), str(temp_insights / f"{novo_stem}.insights.json"))

        novas_transcricoes.append(novo_txt_name)

    # Processar mídias em AUDIOS_DIR
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

    # Mover de volta
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

    if RELATORIO_CSV.exists():
        RELATORIO_CSV.unlink()

    print("\n" + "🎉" * 20)
    print("BASE REORGANIZADA APENAS COM PREGAÇÕES E ENSINAMENTOS VÁLIDOS!")
    print(f"• {len(sem_pregacao)} transcrições sem pregação removidas")
    print(f"• {media_deletadas} áudios sem pregação removidos")
    print(f"• {len(pregacoes_validas)} PREGAÇÕES REALMENTE ÚTEIS indexadas de 001 a {len(pregacoes_validas):03d}")
    print("🎉" * 20 + "\n")

if __name__ == "__main__":
    main()
