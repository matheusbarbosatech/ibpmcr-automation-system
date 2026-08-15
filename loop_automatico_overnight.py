"""
Loop Automático Overnight - IBPM CR Transcrição via Kaggle GPU
==============================================================
Roda em ciclos automáticos durante a noite:
1. Detecta cultos ainda não transcritos
2. Atualiza a lista de pendentes para o próximo batch
3. Dispara GPU no Kaggle e aguarda conclusão
4. Baixa os resultados
5. Repete até 100% concluído ou sem mais progresso

Uso:
    python loop_automatico_overnight.py
"""

import os
import sys
import re
import time
import subprocess
from pathlib import Path
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
TRANSCRICOES_DIR = BASE_DIR / "data" / "audio_podcasts" / "transcricoes_fase2"
LISTA_PENDENTES = BASE_DIR / "data" / "lista_audios_sem_transcricao.txt"
KERNEL_REF = "omatheusbsilva/ibpmcr-whisper-gpu"
LOG_LOOP = BASE_DIR / "logs" / "loop_overnight.log"

LOG_LOOP.parent.mkdir(parents=True, exist_ok=True)
TRANSCRICOES_DIR.mkdir(parents=True, exist_ok=True)


def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(msg):
    linha = f"[{ts()}] {msg}"
    print(linha)
    sys.stdout.flush()
    with open(LOG_LOOP, "a", encoding="utf-8") as f:
        f.write(linha + chr(10))


def extrair_video_id(filename):
    match = re.search(r'_([a-zA-Z0-9_-]{11})_', str(filename))
    return match.group(1) if match else None


def obter_lista_original():
    pendentes = []
    if LISTA_PENDENTES.exists():
        with open(LISTA_PENDENTES, "r", encoding="utf-8") as f:
            for line in f:
                l = line.strip()
                if l and not l.startswith("#"):
                    pendentes.append(l)
    return pendentes


def obter_ja_transcritos():
    ja = set()
    for txt_file in TRANSCRICOES_DIR.glob("*.txt"):
        if txt_file.name == "execution_log.txt":
            continue
        vid = extrair_video_id(txt_file.stem)
        if vid:
            ja.add(vid)
    return ja


def calcular_pendentes_restantes():
    todos = obter_lista_original()
    ja_feitos = obter_ja_transcritos()
    return [a for a in todos if extrair_video_id(a) and extrair_video_id(a) not in ja_feitos]


def atualizar_lista_pendentes(restantes):
    with open(LISTA_PENDENTES, "w", encoding="utf-8") as f:
        f.write("# LISTA ATUALIZADA AUTOMATICAMENTE PELO LOOP OVERNIGHT" + chr(10))
        for audio in restantes:
            f.write(audio + chr(10))
    log(f"  Lista atualizada: {len(restantes)} pendentes.")


def aguardar_kaggle_concluir(timeout_minutos=120, intervalo_seg=20):
    deadline = time.time() + timeout_minutos * 60
    while time.time() < deadline:
        try:
            res = subprocess.run(
                ["kaggle", "kernels", "status", KERNEL_REF],
                capture_output=True, text=True, timeout=30
            )
            status = res.stdout.strip()
            if "COMPLETE" in status:
                return "COMPLETE"
            elif "ERROR" in status:
                return "ERROR"
            else:
                log(f"  GPU: {status}")
        except Exception as e:
            log(f"  [AVISO] Erro ao checar status: {e}")
        time.sleep(intervalo_seg)
    return "TIMEOUT"


def baixar_resultados():
    log("  Baixando resultados do Kaggle...")
    cmd = ["kaggle", "kernels", "output", KERNEL_REF, "-p", str(TRANSCRICOES_DIR)]
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                   errors="ignore", env=env, timeout=300)
    txts = [f for f in TRANSCRICOES_DIR.glob("*.txt") if f.name != "execution_log.txt"]
    log(f"  Download OK. Total transcrições locais: {len(txts)}")


def disparar_gpu():
    log("  Gerando notebook e enviando para Kaggle GPU...")
    res = subprocess.run(
        [sys.executable, "rodar_gpu_nuvem.py", "--no-monitor"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
        cwd=str(BASE_DIR), timeout=120
    )
    if res.returncode == 0:
        log("  Kernel enviado com sucesso!")
        return True
    else:
        log(f"  [ERRO] Falha: {res.stderr[-400:]}")
        return False


def main():
    log("=" * 65)
    log("  IBPM CR - LOOP AUTOMATICO OVERNIGHT (GPU Kaggle)")
    log("  Roda até 100% ou 10 ciclos. Boa noite!")
    log("=" * 65)

    os.environ["KAGGLE_API_TOKEN"] = "KGAT_0193e0e51c366c39a247e46035238ef8"
    kaggle_dir = Path.home() / ".kaggle"
    kaggle_dir.mkdir(parents=True, exist_ok=True)
    (kaggle_dir / "access_token").write_text("KGAT_0193e0e51c366c39a247e46035238ef8")

    MAX_CICLOS = 10
    ciclo = 0
    sem_progresso = 0

    while ciclo < MAX_CICLOS:
        ciclo += 1
        log(f"\n{'='*65}")
        log(f"  CICLO {ciclo}/{MAX_CICLOS}")
        log(f"{'='*65}")

        restantes = calcular_pendentes_restantes()
        ja_ok = len(obter_ja_transcritos())
        log(f"  Transcritos: {ja_ok} | Pendentes: {len(restantes)}")

        if not restantes:
            log("\nALL DONE! 100% das transcricoes concluidas!")
            break

        atualizar_lista_pendentes(restantes)

        # Aguarda atual run se necessário (primeiro ciclo pode ter um em andamento)
        if ciclo == 1:
            res_check = subprocess.run(
                ["kaggle", "kernels", "status", KERNEL_REF],
                capture_output=True, text=True
            )
            if "RUNNING" in res_check.stdout or "QUEUED" in res_check.stdout:
                log("  GPU ja esta rodando! Aguardando conclusao...")
                status_final = aguardar_kaggle_concluir(timeout_minutos=120)
                log(f"  Status: {status_final}")
                baixar_resultados()
                restantes = calcular_pendentes_restantes()
                ja_ok = len(obter_ja_transcritos())
                log(f"  Apos 1o run: {ja_ok} transcritos, {len(restantes)} pendentes")
                if not restantes:
                    log("\nALL DONE! 100% concluido!")
                    break
                atualizar_lista_pendentes(restantes)
                time.sleep(30)

        ok = disparar_gpu()
        if not ok:
            log("  Falha ao enviar. Tentando novamente em 90s...")
            time.sleep(90)
            continue

        log("  Aguardando Kaggle aceitar job (45s)...")
        time.sleep(45)

        log("  Aguardando GPU concluir (max 120min)...")
        status_final = aguardar_kaggle_concluir(timeout_minutos=120, intervalo_seg=20)
        log(f"  GPU finalizou: {status_final}")

        baixar_resultados()

        novos_restantes = calcular_pendentes_restantes()
        progresso = len(restantes) - len(novos_restantes)
        log(f"  Progresso: +{progresso} novas transcrições")

        if progresso == 0:
            sem_progresso += 1
            log(f"  Sem progresso ({sem_progresso}/3). Possível bloqueio YouTube.")
            if sem_progresso >= 3:
                log("  PARADA: 3 ciclos sem avanço. Encerrando.")
                break
        else:
            sem_progresso = 0

        if novos_restantes and status_final != "TIMEOUT":
            log("  Proximo ciclo em 30s...")
            time.sleep(30)

    log("\n" + "="*65)
    log("  RELATORIO FINAL")
    log("="*65)
    final = len(obter_ja_transcritos())
    total = len(obter_lista_original())
    log(f"  Transcrições: {final} de {total+final} originais")
    for r in calcular_pendentes_restantes()[:5]:
        log(f"  Ainda pendente: {r}")
    log("  Loop encerrado. Bom dia!")
    log("="*65)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("\nLoop interrompido pelo usuario (Ctrl+C). Transcricoes salvas.")
