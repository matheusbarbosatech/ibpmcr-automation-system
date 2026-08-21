"""
Script de Teste Oficial: Download de Trecho do Primeiro Culto de Agosto/2026 + Upscale 4K via FFmpeg.
Video Target: DOMINGO - SANTA CEIA (02/08/26) [ID: uu8a3Rtvcgk]
"""

import sys
import os
import json
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / "cookies.txt"

OUT_DIR = BASE_DIR / "data" / "fase3_renderizacao" / "teste_4k"
OUT_DIR.mkdir(parents=True, exist_ok=True)

V1080_FILE = OUT_DIR / "culto_02_08_2026_1080p_sample.mp4"
V4K_FILE = OUT_DIR / "culto_02_08_2026_4K_upscaled.mp4"

print("=======================================================================")
print("🚀 TESTE IBPM CR: DOWNLOAD DO CULTO (02/08/2026) E UPSCALE PARA 4K")
print("=======================================================================")
print(f"📌 Vídeo Alvo: DOMINGO - SANTA CEIA (02/08/26)")
print(f"📌 Output 1080p: {V1080_FILE}")
print(f"📌 Output 4K:    {V4K_FILE}")
print("-----------------------------------------------------------------------")

# PASSO 1: Obter URLs de Stream via yt-dlp
print("\n[1/3] Obtendo links de stream 1080p do YouTube (yt-dlp + Node.js JS Runtime)...")

cmd_url = [
    "yt-dlp",
    "--cookies", str(COOKIES_FILE),
    "--js-runtimes", "node",
    "-g",
    "-f", "bestvideo[height<=1080]+bestaudio/best",
    "https://www.youtube.com/watch?v=uu8a3Rtvcgk"
]

res_url = subprocess.run(cmd_url, capture_output=True, text=True)
urls = [u.strip() for u in res_url.stdout.strip().split('\n') if u.strip()]

if not urls:
    print("❌ Erro ao obter URLs do YouTube:", res_url.stderr)
    sys.exit(1)

print(f"✅ Streams obtidos com sucesso! ({len(urls)} stream(s))")

# PASSO 2: Download/Corte de 30 segundos do vídeo 1080p via FFmpeg
print("\n[2/3] Baixando amostra de 30 segundos do culto em 1080p (00:20:00 - 00:20:30)...")

if len(urls) >= 2:
    v_url, a_url = urls[0], urls[1]
    cmd_cut = [
        "ffmpeg", "-y",
        "-ss", "00:20:00", "-i", v_url,
        "-ss", "00:20:00", "-i", a_url,
        "-t", "00:00:30",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(V1080_FILE)
    ]
else:
    cmd_cut = [
        "ffmpeg", "-y",
        "-ss", "00:20:00", "-i", urls[0],
        "-t", "00:00:30",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        str(V1080_FILE)
    ]

res_cut = subprocess.run(cmd_cut, capture_output=True, text=True)
if not V1080_FILE.exists() or V1080_FILE.stat().st_size == 0:
    print("❌ Erro ao recortar vídeo 1080p:", res_cut.stderr)
    sys.exit(1)

size_1080_mb = V1080_FILE.stat().st_size / (1024 * 1024)
print(f"✅ Vídeo 1080p baixado com sucesso! Tamanho: {size_1080_mb:.2f} MB")

# PASSO 3: Upscale de 1080p (1920x1080) para 4K UHD (3840x2160) com filtro Lanczos
print("\n[3/3] Executando UPSCALE PARA 4K UHD (3840x2160) via FFmpeg (Lanczos + High Profile H.264)...")

cmd_upscale = [
    "ffmpeg", "-y",
    "-i", str(V1080_FILE),
    "-vf", "scale=3840:2160:flags=lanczos,unsharp=5:5:1.0:5:5:0.0",
    "-c:v", "libx264",
    "-preset", "medium",
    "-crf", "18",
    "-pix_fmt", "yuv420p",
    "-c:a", "copy",
    str(V4K_FILE)
]

res_up = subprocess.run(cmd_upscale, capture_output=True, text=True)

if not V4K_FILE.exists() or V4K_FILE.stat().st_size == 0:
    print("❌ Erro no upscale para 4K:", res_up.stderr)
    sys.exit(1)

size_4k_mb = V4K_FILE.stat().st_size / (1024 * 1024)
print(f"🎉 UPSCALE CONCLUÍDO COM SUCESSO!")
print(f"📁 Arquivo 4K Final: {V4K_FILE}")
print(f"📦 Tamanho do Arquivo 4K: {size_4k_mb:.2f} MB")

# PASSO 4: Verificação de Resolução via FFprobe
print("\n🔍 Verificando Metadados do Arquivo 4K com FFprobe...")
cmd_probe = [
    "ffprobe",
    "-v", "error",
    "-select_streams", "v:0",
    "-show_entries", "stream=width,height,codec_name,r_frame_rate",
    "-of", "json",
    str(V4K_FILE)
]

res_probe = subprocess.run(cmd_probe, capture_output=True, text=True)
print("Metadados:", res_probe.stdout.strip())
