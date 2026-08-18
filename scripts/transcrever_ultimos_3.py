import json
from pathlib import Path
from faster_whisper import WhisperModel

audios_dir = Path("data/audios_faltantes")
txt_dir = Path("data/transcriptions/txt")
json_dir = Path("data/transcriptions/json")

txt_dir.mkdir(parents=True, exist_ok=True)
json_dir.mkdir(parents=True, exist_ok=True)

target_stems = ["154_eCrTjaH1j7I", "158_kSxBUPt9Bvg", "162_lcQfI-svRrA"]

print("==============================================================")
print("🚀 TRANSCREVENDO OS ÚLTIMOS 3 CULTOS NA SUA MÁQUINA LOCAL...")
print("==============================================================\n")

model = WhisperModel("tiny", device="cpu", compute_type="int8")

for stem in target_stems:
    candidatos = list(audios_dir.glob(f"{stem}*"))
    if not candidatos:
        print(f"⚠️ Áudio não encontrado: {stem}")
        continue
    arq = candidatos[0]
    out_txt = txt_dir / f"{arq.stem}.txt"
    out_json = json_dir / f"{arq.stem}.json"
    
    if out_txt.exists():
        print(f"✅ Já transcrito: {arq.name}")
        continue
        
    print(f"Transcrevendo: {arq.name}...")
    try:
        segments, info = model.transcribe(str(arq), language="pt", beam_size=3, vad_filter=True)
        texto = " ".join([s.text.strip() for s in segments if s.text.strip()])
        if not texto:
            texto = f"[AVISO DE TRANSCRIÇÃO: Áudio de vinheta/música sem fala humana. Duração: {info.duration:.1f}s]"
            
        out_txt.write_text(texto, encoding="utf-8")
        out_json.write_text(json.dumps({"file": arq.name, "text": texto}, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"  ✅ Concluído: {arq.name} ({len(texto.split())} palavras)")
    except Exception as e:
        print(f"  ❌ Erro: {e}")

print("\n==============================================================")
total_txt = len(list(txt_dir.glob("*.txt")))
print(f"🎉 CELEBRAÇÃO! TOTAL FINAL NO SEU PC: {total_txt} / 455 TRANSCRIÇÕES!")
print("==============================================================")
