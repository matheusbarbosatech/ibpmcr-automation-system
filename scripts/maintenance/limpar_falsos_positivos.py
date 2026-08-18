import os
import sys
import shutil
import re
import json
from pathlib import Path

# Suporte UTF-8 no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent.parent
STREAMS_DIR = BASE_DIR / "data" / "transcriptions"
TXT_DIR = STREAMS_DIR / "txt"
JSON_DIR = STREAMS_DIR / "json"
FALSOS_POSITIVOS_DIR = STREAMS_DIR / "falsos_positivos"

TERMOS_FALSO_POSITIVO = [
    "Pular navegação",
    "Fazer login",
    "Inscrever-se",
    "pular navegação",
    "fazer login",
    "inscrever-se"
]

def extrair_video_id(filename: str) -> str:
    """Extrai o video_id de 11 caracteres a partir do nome do arquivo."""
    m = re.search(r'(?:transcricao_|^\d{3}_)?([a-zA-Z0-9_-]{11})(?:_|$)', filename)
    if m:
        return m.group(1)
    return filename.split('.')[0]

def limpar_falsos_positivos():
    FALSOS_POSITIVOS_DIR.mkdir(parents=True, exist_ok=True)
    
    # Coletar arquivos já movidos anteriormente para manter o histórico completo
    falsos_positivos_ids = []
    if FALSOS_POSITIVOS_DIR.exists():
        for p in FALSOS_POSITIVOS_DIR.glob("*.txt"):
            v_id = extrair_video_id(p.name)
            if v_id and v_id not in falsos_positivos_ids:
                falsos_positivos_ids.append(v_id)

    # Coletar todos os arquivos .txt em data/transcriptions/txt/
    arquivos_txt = set()
    if TXT_DIR.exists():
        for p in TXT_DIR.glob("*.txt"):
            if FALSOS_POSITIVOS_DIR not in p.parents:
                arquivos_txt.add(p)

    falsos_positivos_movidos = 0
    transcricoes_reais = 0

    print("=" * 80)
    print("🧹 VARRENDO E ANALISANDO TRANSCRIÇÕES PARA REMOÇÃO DE FALSOS POSITIVOS...")
    print("=" * 80)

    for txt_path in sorted(arquivos_txt):
        try:
            content = txt_path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        video_id = extrair_video_id(txt_path.name)

        is_falso_positivo = False
        for termo in TERMOS_FALSO_POSITIVO:
            if termo in content:
                is_falso_positivo = True
                break

        if is_falso_positivo:
            falsos_positivos_movidos += 1
            falsos_positivos_ids.append(video_id)
            
            # Mover o arquivo .txt para a pasta de falsos positivos
            dest_txt = FALSOS_POSITIVOS_DIR / txt_path.name
            shutil.move(str(txt_path), str(dest_txt))
            print(f"❌ Falso positivo detectado e movido: {txt_path.name} (ID: {video_id})")

            # Se houver arquivo JSON correspondente, mover também
            json_name = txt_path.name.replace(".txt", ".json")
            json_path = JSON_DIR / json_name
            if json_path.exists():
                dest_json = FALSOS_POSITIVOS_DIR / json_name
                shutil.move(str(json_path), str(dest_json))
        else:
            transcricoes_reais += 1

    json_falsos_file = BASE_DIR / "data" / "falsos_positivos_ids.json"
    json_falsos_file.write_text(json.dumps(falsos_positivos_ids, indent=2, ensure_ascii=False), encoding="utf-8")

    print("\n" + "=" * 80)
    print("📊 RELATÓRIO FINAL DE LIMPEZA DE FALSOS POSITIVOS")
    print("=" * 80)
    print(f"✅ Transcrições REAIS mantidas: {transcricoes_reais}")
    print(f"🚨 Falsos positivos movidos: {falsos_positivos_movidos}")
    print(f"📁 Pasta de destino dos falsos positivos: {FALSOS_POSITIVOS_DIR}")
    print(f"📄 Lista salva em JSON: {json_falsos_file}")
    print("-" * 80)
    print(f"📋 Lista dos video_ids falsos positivos ({len(falsos_positivos_ids)}):")
    print(falsos_positivos_ids)
    print("=" * 80 + "\n")

if __name__ == "__main__":
    limpar_falsos_positivos()
