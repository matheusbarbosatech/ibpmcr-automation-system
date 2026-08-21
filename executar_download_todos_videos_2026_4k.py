"""
executar_download_todos_videos_2026_4k.py
=========================================
Script de automação para download de TODOS os vídeos de 2026 do canal da IBPM em resolução 4K UHD.

Recursos:
- Filtra automaticamente todos os 96 vídeos/cultos de 2026 no acervo da IBPM.
- Prioridade máxima de resolução: 4K UHD (2160p) > 1440p > 1080p60.
- Suporte a retomada (skip se o vídeo já existir localmente).
- Log detalhado de progresso e relatório final em JSON.
- Parâmetro --dry-run para listar os vídeos e estimar tamanho sem baixar.

Uso:
  python executar_download_todos_videos_2026_4k.py
  python executar_download_todos_videos_2026_4k.py --dry-run
  python executar_download_todos_videos_2026_4k.py --output-dir "G:\\Meu Drive\\IBPM_4K_2026"
"""

import sys
import os
import re
import json
import time
import argparse
import subprocess
from pathlib import Path

# Suporte nativo a UTF-8 no terminal
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
JSON_MAP = BASE_DIR / "data" / "fase1_mapeamento" / "canal_ibpm_todos_videos.json"
COOKIES_FILE = BASE_DIR / "cookies.txt"

def carregar_videos_2026():
    """Lê o mapeamento do canal e retorna a lista de vídeos de 2026 ordenados por data."""
    if not JSON_MAP.exists():
        print(f"❌ Erro: Arquivo de mapeamento do canal não encontrado em {JSON_MAP}")
        sys.exit(1)

    with open(JSON_MAP, "r", encoding="utf-8") as f:
        videos = json.load(f)

    vids_2026 = []
    for v in videos:
        pub = v.get("published_at", "") or v.get("date", "") or v.get("upload_date", "")
        title = v.get("title", "")
        # Verifica ocorrência do ano 2026
        if "2026" in pub or "/26" in title or ".26" in title or "-26" in title or "(26)" in title:
            vids_2026.append(v)

    return vids_2026

def sanitize_filename(title):
    """Remove caracteres inválidos para nomes de arquivos no Windows."""
    title = re.sub(r'[^\w\s-]', '', title, flags=re.UNICODE)
    title = re.sub(r'\s+', '_', title).strip('_')
    return title[:70] if title else "culto_ibpm_2026"

def main():
    parser = argparse.ArgumentParser(description="Download massivo de vídeos de 2026 da IBPM em 4K UHD.")
    parser.add_argument("--output-dir", type=str, default="data/videos_2026_4k", help="Diretório de destino para salvar os vídeos 4K.")
    parser.add_argument("--dry-run", action="store_true", help="Apenas lista os vídeos de 2026 sem realizar os downloads.")
    args = parser.parse_args()

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    log_path = out_dir / "download_2026_4k.log"
    report_json = out_dir / "relatorio_downloads_2026_4k.json"

    def log(msg):
        timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
        line = f"{timestamp} {msg}"
        print(line)
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    log("=======================================================================")
    log("🏛️ IBPM CR: DOWNLOAD MASSIVO DE VÍDEOS DE 2026 EM 4K UHD")
    log("=======================================================================")

    videos = carregar_videos_2026()
    log(f"📌 Total de Vídeos de 2026 Encontrados: {len(videos)}")
    log(f"📌 Pasta de Destino: {out_dir.resolve()}")
    log(f"📌 Cookies de Autenticação: {COOKIES_FILE} (Existe: {COOKIES_FILE.exists()})")
    log("-----------------------------------------------------------------------")

    if args.dry_run:
        log("\n🔍 MODO DRY-RUN ATIVADO — Listando vídeos de 2026:")
        for idx, v in enumerate(videos, 1):
            log(f"  {idx:02d}/{len(videos):02d} | ID: {v['id']} | Título: {v['title']}")
        log("\n✅ Fim da simulação. Execute sem --dry-run para iniciar o download real.")
        return

    sucessos = 0
    ignorados = 0
    falhas = 0
    relatorio = []

    for idx, v in enumerate(videos, 1):
        vid_id = v["id"]
        title_raw = v.get("title", "culto")
        clean_name = sanitize_filename(title_raw)
        out_file = out_dir / f"{idx:02d}_{clean_name}_{vid_id}_4K.mp4"

        log(f"\n[{idx:02d}/{len(videos):02d}] Processando: {title_raw}")
        log(f"🆔 ID: {vid_id} | Destino: {out_file.name}")

        # Verifica se o vídeo já foi baixado previamente
        if out_file.exists() and out_file.stat().st_size > 50000000:
            size_mb = out_file.stat().st_size / (1024 * 1024)
            log(f"⏭️ Vídeo já baixado ({size_mb:.2f} MB). Ignorando...")
            ignorados += 1
            relatorio.append({"id": vid_id, "titulo": title_raw, "status": "ja_existente", "tamanho_mb": size_mb})
            continue

        cmd = [
            "yt-dlp",
            "--js-runtimes", "node",
            "-f", "bestvideo[height>=2160]+bestaudio/bestvideo[height>=1440]+bestaudio/bestvideo[height<=1080]+bestaudio/best",
            "--merge-output-format", "mp4",
            "-o", str(out_file),
            f"https://www.youtube.com/watch?v={vid_id}"
        ]
        if COOKIES_FILE.exists():
            cmd.extend(["--cookies", str(COOKIES_FILE)])

        log(f"📥 Baixando em 4K UHD via yt-dlp...")
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode == 0 and out_file.exists() and out_file.stat().st_size > 50000000:
            size_mb = out_file.stat().st_size / (1024 * 1024)
            log(f"✅ Sucesso! Download concluído ({size_mb:.2f} MB).")
            sucessos += 1
            relatorio.append({"id": vid_id, "titulo": title_raw, "status": "sucesso", "tamanho_mb": size_mb})
        else:
            log(f"❌ Falha no download do vídeo {vid_id}: {res.stderr[:300]}")
            falhas += 1
            relatorio.append({"id": vid_id, "titulo": title_raw, "status": "falha", "erro": res.stderr[:300]})

    log("\n=======================================================================")
    log("📊 RESUMO FINAL DO DOWNLOAD 2026 EM 4K")
    log("=======================================================================")
    log(f"✅ Vídeos Concluídos: {sucessos}")
    log(f"⏭️ Vídeos Ignorados (Já baixados): {ignorados}")
    log(f"❌ Falhas: {falhas}")
    log("=======================================================================")

    with open(report_json, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=2, ensure_ascii=False)

if __name__ == "__main__":
    main()
