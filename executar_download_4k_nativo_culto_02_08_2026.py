"""
Script de Download Direto da Faixa 4K UHD Nativa do YouTube.
Culto: DOMINGO - SANTA CEIA (02/08/26) [ID: uu8a3Rtvcgk]
"""

import sys
import os
import time
import subprocess
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent
COOKIES_FILE = BASE_DIR / "cookies.txt"

OUT_DIR = BASE_DIR / "data" / "fase3_renderizacao" / "culto_completo_4k"
OUT_DIR.mkdir(parents=True, exist_ok=True)

OUT_4K_NATIVO = OUT_DIR / "DOMINGO_SANTA_CEIA_02_08_2026_4K_NATIVO.mp4"

print("=======================================================================")
print("🚀 DOWNLOAD DIRETO DA FAIXA 4K UHD NATIVA DO YOUTUBE (3840x2160)")
print("=======================================================================")
print(f"📌 Culto: DOMINGO - SANTA CEIA (02/08/26) [ID: uu8a3Rtvcgk]")
print(f"📌 Arquivo de Saída: {OUT_4K_NATIVO}")
print("-----------------------------------------------------------------------")

cmd = [
    "yt-dlp",
    "--cookies", str(COOKIES_FILE),
    "--js-runtimes", "node",
    "-f", "401+140/bestvideo[height>=2160]+bestaudio/best",
    "--merge-output-format", "mp4",
    "-o", str(OUT_4K_NATIVO),
    "https://www.youtube.com/watch?v=uu8a3Rtvcgk"
]

print("📥 Baixando faixa 4K (3840x2160 60fps) do YouTube...")
start = time.time()
res = subprocess.run(cmd, capture_output=True, text=True)
elapsed = time.time() - start

if res.returncode == 0 and OUT_4K_NATIVO.exists():
    size_gb = OUT_4K_NATIVO.stat().st_size / (1024**3)
    print(f"\n🎉 DOWNLOAD 4K NATIVO CONCLUÍDO COM SUCESSO em {elapsed/60:.1f} minutos!")
    print(f"📦 Arquivo: {OUT_4K_NATIVO}")
    print(f"📊 Tamanho Final: {size_gb:.2f} GB")
else:
    print(f"❌ Erro no download 4K nativo: {res.stderr}")
