"""
auditar_e_refazer_transcricoes.py
==================================
Verifica todas as transcricoes em transcricoes_fase2/, classifica cada uma,
deleta as incompletas, adiciona de volta a lista de pendentes e dispara
automaticamente uma nova rodada na GPU do Kaggle.

Criterios de TRANSCRICAO INCOMPLETA:
  - VAZIA:         arquivo tem so o cabecalho (< 200 bytes ou < 5 linhas)
  - SEM_TIMESTAMP: arquivo tem 1 unica linha (blob sem [HH:MM:SS])
  - MUITO_CURTA:   arquivo < 3000 bytes E < 40 linhas (pouco conteudo p/ 1h+ de culto)

Uso:
    python auditar_e_refazer_transcricoes.py           (auditoria + dispara GPU se necessario)
    python auditar_e_refazer_transcricoes.py --dry-run (so relatorio, sem deletar nem disparar)
"""

import re
import sys
import os
import json
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
TRANS_DIR = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
LISTA_PENDENTES = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"
RELATORIO = BASE_DIR / "data" / "auditoria_transcricoes.txt"

DRY_RUN = "--dry-run" in sys.argv

# ─────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────

def ts():
    return datetime.now().strftime("%H:%M:%S")

def log(msg):
    print(f"[{ts()}] {msg}")
    sys.stdout.flush()

def get_vid(name):
    m = re.search(r'_([a-zA-Z0-9_-]{11})_', str(name))
    return m.group(1) if m else None

def classificar(txt_path):
    """Retorna (status, detalhes) para uma transcricao."""
    try:
        size = txt_path.stat().st_size
        content = txt_path.read_text(encoding='utf-8', errors='ignore').strip()
        lines = [l for l in content.split('\n') if l.strip()]
        num_lines = len(lines)
        has_timestamp = bool(re.search(r'\[\d{2}:\d{2}:\d{2}\]', content))
        num_timestamps = len(re.findall(r'\[\d{2}:\d{2}:\d{2}\]', content))

        if size < 200 or num_lines <= 3:
            return "VAZIA", f"{size}b / {num_lines}L"
        if num_timestamps == 0 and num_lines <= 5:
            return "VAZIA", f"{size}b / {num_lines}L (sem conteudo)"
        if num_lines == 1 and size > 5000:
            return "SEM_TIMESTAMP", f"{size}b / blob unico (sem timestamps)"
        if not has_timestamp and size < 5000:
            return "SEM_TIMESTAMP", f"{size}b / sem [HH:MM:SS]"
        if size < 3000 and num_lines < 40:
            return "MUITO_CURTA", f"{size}b / {num_lines}L / {num_timestamps} timestamps"
        return "OK", f"{size:,}b / {num_lines}L / {num_timestamps} timestamps"
    except Exception as e:
        return "ERRO_LEITURA", str(e)

# ─────────────────────────────────────────────────
# Auditoria
# ─────────────────────────────────────────────────

log("=" * 65)
log("  AUDITORIA DE TRANSCRICOES - IBPM CR")
if DRY_RUN:
    log("  MODO: DRY-RUN (nenhum arquivo sera deletado)")
else:
    log("  MODO: EXECUCAO (arquivos incompletos serao deletados e reenfileirados)")
log("=" * 65)

txts = sorted([f for f in TRANS_DIR.glob("*.txt") if f.name != "execution_log.txt"])
log(f"  Arquivos .txt encontrados: {len(txts)}")

contagem = {"OK": 0, "VAZIA": 0, "SEM_TIMESTAMP": 0, "MUITO_CURTA": 0, "ERRO_LEITURA": 0}
incompletas = []  # lista de (Path, status, detalhes)

for f in txts:
    status, detalhes = classificar(f)
    contagem[status] = contagem.get(status, 0) + 1
    if status != "OK":
        incompletas.append((f, status, detalhes))

log(f"\n  RESUMO:")
log(f"    OK (completas):         {contagem['OK']}")
log(f"    VAZIA (so cabecalho):   {contagem.get('VAZIA', 0)}")
log(f"    SEM_TIMESTAMP (blob):   {contagem.get('SEM_TIMESTAMP', 0)}")
log(f"    MUITO_CURTA:            {contagem.get('MUITO_CURTA', 0)}")
log(f"    ERRO_LEITURA:           {contagem.get('ERRO_LEITURA', 0)}")
log(f"    Total incompletas:      {len(incompletas)}")

if incompletas:
    log(f"\n  DETALHES DAS INCOMPLETAS:")
    for f, status, detalhes in incompletas:
        vid = get_vid(f.stem) or "???"
        log(f"    [{status:15}] {vid} | {detalhes} | {f.name}")

# Salvar relatorio em arquivo
with open(RELATORIO, "w", encoding="utf-8") as rf:
    rf.write(f"AUDITORIA IBPM CR - {datetime.now()}\n")
    rf.write(f"Total arquivos: {len(txts)}\n")
    rf.write(f"Completas: {contagem['OK']}\n")
    rf.write(f"Incompletas: {len(incompletas)}\n\n")
    for f, status, detalhes in incompletas:
        rf.write(f"[{status}] {f.name} | {detalhes}\n")

log(f"\n  Relatorio salvo em: {RELATORIO}")

if not incompletas:
    log("\n  TODAS AS TRANSCRICOES ESTAO COMPLETAS!")
    sys.exit(0)

if DRY_RUN:
    log("\n  DRY-RUN: nada foi alterado. Rode sem --dry-run para executar.")
    sys.exit(0)

# ─────────────────────────────────────────────────
# Deletar incompletas e reconstruir lista pendentes
# ─────────────────────────────────────────────────

log(f"\n  Deletando {len(incompletas)} transcricoes incompletas...")
vids_para_refazer = set()
nomes_para_refazer = []

for f, status, detalhes in incompletas:
    vid = get_vid(f.stem)
    if vid:
        vids_para_refazer.add(vid)
        # Reconstruir nome de audio original (.webm)
        nome_webm = f.stem + ".webm"
        nomes_para_refazer.append(nome_webm)
    f.unlink()
    log(f"    [DELETADO] {f.name}")

# Ler lista atual de pendentes (para nao duplicar)
pendentes_atuais = []
if LISTA_PENDENTES.exists():
    pendentes_atuais = [
        l.strip() for l in LISTA_PENDENTES.read_text(encoding='utf-8').split('\n')
        if l.strip() and not l.startswith('#')
    ]

# Juntar: refazer primeiro + pendentes que nao foram feitos
todos_pendentes = list(nomes_para_refazer)
ja_refazer_vids = set(get_vid(n) for n in nomes_para_refazer if get_vid(n))

for p in pendentes_atuais:
    vid = get_vid(p)
    if vid and vid not in vids_para_refazer:
        todos_pendentes.append(p)

log(f"\n  Lista atualizada: {len(todos_pendentes)} pendentes")
log(f"    {len(nomes_para_refazer)} para REFAZER + {len(todos_pendentes)-len(nomes_para_refazer)} novos pendentes")

with open(LISTA_PENDENTES, "w", encoding="utf-8") as f:
    f.write(f"# Lista atualizada automaticamente - {datetime.now()}\n")
    f.write(f"# {len(nomes_para_refazer)} para refazer + {len(todos_pendentes)-len(nomes_para_refazer)} pendentes\n")
    for item in todos_pendentes:
        f.write(item + "\n")

log(f"  Lista salva em: {LISTA_PENDENTES}")

# ─────────────────────────────────────────────────
# Disparar nova rodada na GPU
# ─────────────────────────────────────────────────

log(f"\n  Disparando nova rodada na GPU do Kaggle...")
res = subprocess.run(
    [sys.executable, "rodar_gpu_nuvem.py", "--no-monitor"],
    capture_output=True, text=True, encoding='utf-8', errors='ignore',
    cwd=str(BASE_DIR)
)

if res.returncode == 0:
    log("  GPU disparada com sucesso! Use 'python rodar_gpu_nuvem.py --monitor-only' para acompanhar.")
else:
    log(f"  [ERRO] Falha ao disparar GPU: {res.stderr[-300:]}")

log("\n  AUDITORIA CONCLUIDA.")
log("=" * 65)
