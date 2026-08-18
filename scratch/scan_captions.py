import json
import subprocess
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
MASTER_VIDEOS_JSON = BASE_DIR / "data" / "canal_ibpm_todos_videos.json"

def scan_sample():
    with open(MASTER_VIDEOS_JSON, "r", encoding="utf-8") as f:
        videos = json.load(f)

    streams = [v for v in videos if v.get("source_tab") == "streams"]
    print(f"Total de streams no canal: {len(streams)}")

    sample = streams[:15]
    has_sub = 0
    no_sub = 0

    for i, v in enumerate(sample):
        v_id = v["id"]
        title = v.get("title", "")[:40]
        
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "--flat-playlist",
            "--dump-json",
            f"https://www.youtube.com/watch?v={v_id}"
        ]
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
            info = json.loads(res.stdout)
            subs = info.get("subtitles", {})
            auto = info.get("automatic_captions", {})

            has_pt = ("pt" in subs or "pt-BR" in subs or "pt" in auto or "pt-BR" in auto or "pt-orig" in auto)
            if has_pt:
                has_sub += 1
                status = "✅ LEGENDAS ENCONTRADAS"
            else:
                no_sub += 1
                status = "❌ SEM LEGENDA (REQUER WHISPER)"

            print(f"[{i+1}/15] ID: {v_id} | {title} | {status}")
            
        except Exception as e:
            print(f"[{i+1}/15] ID: {v_id} | Erro: {e}")

    print(f"\nResultado da amostra (15 streams):")
    print(f" - Com legendas no YouTube: {has_sub}")
    print(f" - Sem legendas (requer transcrição de áudio): {no_sub}")

if __name__ == "__main__":
    scan_sample()
