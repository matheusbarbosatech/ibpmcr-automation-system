"""
Script de Automação IBPM CR: Download do Culto Completo (02/08/2026) + Upscale em 4K.
Video Target: DOMINGO - SANTA CEIA (02/08/26) [ID: uu8a3Rtvcgk]
Duração: 2h 47min 27seg (10.047s)
"""

import sys
import os
import json
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / "cookies.txt"

OUT_DIR = BASE_DIR / "data" / "fase3_renderizacao" / "culto_completo_4k"
OUT_DIR.mkdir(parents=True, exist_ok=True)

V1080_FULL = OUT_DIR / "DOMINGO_SANTA_CEIA_02_08_2026_1080p.mp4"
V4K_UPSCALE = OUT_DIR / "DOMINGO_SANTA_CEIA_02_08_2026_4K_UPSCALE.mp4"
LOG_FILE = OUT_DIR / "processamento.log"

def log(msg):
    timestamp = time.strftime("[%Y-%m-%d %H:%M:%S]")
    line = f"{timestamp} {msg}"
    print(line)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")

log("=======================================================================")
log("🏛️ IBPM CR: DOWNLOAD DO CULTO COMPLETO (02/08/2026) + UPSCALE PARA 4K")
log("=======================================================================")
log(f"📌 Culto Alvo: DOMINGO - SANTA CEIA (02/08/26) [ID: uu8a3Rtvcgk]")
log(f"📌 Destino 1080p: {V1080_FULL}")
log(f"📌 Destino 4K Upscale: {V4K_UPSCALE}")
log("-----------------------------------------------------------------------")

# 1. DOWNLOAD DO VÍDEO COMPLETO (1080p)
if not V1080_FULL.exists() or V1080_FULL.stat().st_size < 100000000:
    log("\n[1/3] Iniciando download do CULTO COMPLETO de 2h47m em 1080p60...")
    cmd_download = [
        "yt-dlp",
        "--cookies", str(COOKIES_FILE),
        "--js-runtimes", "node",
        "-f", "bestvideo[height<=1080]+bestaudio/best",
        "--merge-output-format", "mp4",
        "-o", str(V1080_FULL),
        "https://www.youtube.com/watch?v=uu8a3Rtvcgk"
    ]
    res = subprocess.run(cmd_download, capture_output=True, text=True)
    if res.returncode != 0:
        log(f"❌ Erro no download: {res.stderr}")
        sys.exit(1)
    log(f"✅ Download 1080p Concluído! Tamanho: {V1080_FULL.stat().st_size / (1024**3):.2f} GB")
else:
    log(f"ℹ️ Arquivo 1080p completo já existente localmente: {V1080_FULL.stat().st_size / (1024**3):.2f} GB")

# 2. UPSCALE FFmpeg PARA 4K (3840x2160)
log("\n[2/3] Iniciando renderização e UPSCALE PARA 4K UHD (3840x2160)...")
log("⚙️ Aplicando filtro de interpolação Lanczos + Nitidez Unsharp + Codificação H.264...")

log("\n[2/3] Iniciando renderização e UPSCALE PARA 4K UHD (3840x2160)...")
log("⚙️ Aplicando filtro Lanczos + Unsharp + Aceleração GPU Windows Media Foundation (h264_mf)...")

vcodec = "h264_mf"
encoder_args = ["-b:v", "15M"]

cmd_upscale = [
    "ffmpeg", "-y",
    "-i", str(V1080_FULL),
    "-vf", "scale=3840:2160:flags=lanczos,unsharp=5:5:1.0:5:5:0.0",
    "-c:v", vcodec,
    *encoder_args,
    "-pix_fmt", "yuv420p",
    "-c:a", "copy",
    str(V4K_UPSCALE)
]

start_time = time.time()
res_up = subprocess.run(cmd_upscale, capture_output=True, text=True)
elapsed = time.time() - start_time

if res_up.returncode != 0 or not V4K_UPSCALE.exists():
    log(f"❌ Erro na renderização 4K: {res_up.stderr}")
    sys.exit(1)

size_4k_gb = V4K_UPSCALE.stat().st_size / (1024**3)
log(f"\n🎉 PROCESSAMENTO 4K CONCLUÍDO COM SUCESSO em {elapsed/60:.1f} minutos!")
log(f"📦 Arquivo 4K Final: {V4K_UPSCALE}")
log(f"📊 Tamanho Final 4K: {size_4k_gb:.2f} GB")

# 3. VALIDAÇÃO FFPROBE
log("\n[3/3] Auditando arquivo final via FFprobe...")
cmd_probe = [
    "ffprobe", "-v", "error",
    "-select_streams", "v:0",
    "-show_entries", "stream=width,height,codec_name,bit_rate,r_frame_rate",
    "-of", "json", str(V4K_UPSCALE)
]
res_prb = subprocess.run(cmd_probe, capture_output=True, text=True)
log(f"🔍 Metadados FFprobe 4K: {res_prb.stdout.strip()}")
log("=======================================================================")
