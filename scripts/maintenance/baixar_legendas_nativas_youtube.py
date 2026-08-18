import json
import re
import subprocess
from pathlib import Path
from youtube_transcript_api import YouTubeTranscriptApi

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TXT_DIR = BASE_DIR / "data" / "transcriptions" / "txt"
JSON_DIR = BASE_DIR / "data" / "transcriptions" / "json"

TXT_DIR.mkdir(parents=True, exist_ok=True)
JSON_DIR.mkdir(parents=True, exist_ok=True)

targets = [
    {
        "id": "JZqi2LW0Jmw",
        "stem": "JZqi2LW0Jmw_Testemunho_Radical_28_01_24",
        "title": "Testemunho dos Irmaos no Radical (28/01/24)"
    },
    {
        "id": "mJn9p2a9xWs",
        "stem": "455_mJn9p2a9xWs_6_dia_de_festividade_encerramento_16_08_26",
        "title": "6 Dia de Festividade - Encerramento (16/08/26)"
    }
]

print("==============================================================")
print("BAIXANDO TRANSCRIÇOES NATIVAS DO YOUTUBE PARA A PASTA LOCAL")
print("==============================================================")

for t in targets:
    v_id = t["id"]
    stem = t["stem"]
    title = t["title"]
    
    out_txt = TXT_DIR / f"{stem}.txt"
    out_json = JSON_DIR / f"{stem}.json"
    
    print(f"\nBusca de legenda nativa no YouTube para: {title} ({v_id})...")
    
    try:
        data = YouTubeTranscriptApi.get_transcript(v_id, languages=['pt', 'pt-BR', 'en'])
        linhas = [item['text'].strip() for item in data if item['text'].strip()]
        texto_completo = " ".join(linhas)
        palavras = len(texto_completo.split())
        
        out_txt.write_text(texto_completo, encoding="utf-8")
        out_json.write_text(
            json.dumps({"id": v_id, "title": title, "words": palavras, "text": texto_completo}, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        print(f"  [SALVO NO PC DIVERTO DO YOUTUBE]: {out_txt.name} ({palavras} palavras)")
        
    except Exception as e:
        print(f"  Tentando fallback via yt-dlp...")
        tmp_out = BASE_DIR / "data" / "tmp_sub"
        tmp_out.mkdir(exist_ok=True)
        subprocess.run(
            ["yt-dlp", "--write-auto-sub", "--sub-lang", "pt", "--skip-download", "-o", str(tmp_out / "%(id)s.%(ext)s"), f"https://www.youtube.com/watch?v={v_id}"],
            capture_output=True
        )
        vtt_files = list(tmp_out.glob(f"{v_id}*.vtt"))
        if vtt_files:
            vtt_content = vtt_files[0].read_text(encoding="utf-8", errors="replace")
            lines = []
            for l in vtt_content.splitlines():
                if "-->" not in l and not l.startswith("WEBVTT") and not l.isdigit() and l.strip():
                    clean_l = re.sub(r'<[^>]+>', '', l).strip()
                    if clean_l and (not lines or lines[-1] != clean_l):
                        lines.append(clean_l)
            texto_vtt = " ".join(lines)
            out_txt.write_text(texto_vtt, encoding="utf-8")
            out_json.write_text(
                json.dumps({"id": v_id, "title": title, "words": len(texto_vtt.split()), "text": texto_vtt}, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            print(f"  [SALVO NO PC VIA VTT]: {out_txt.name} ({len(texto_vtt.split())} palavras)")
        else:
            print(f"  Erro ao obter legenda nativa: {e}")

print("\n==============================================================")
print("CONCLUIDO! AS TRANSCRIÇOES NATIVAS FORAM COPIADAS PARA O SEU PC!")
print(f"Diretorio TXT: {TXT_DIR}")
print("==============================================================")
