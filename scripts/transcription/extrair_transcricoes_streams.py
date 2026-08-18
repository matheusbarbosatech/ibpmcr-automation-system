"""
Módulo de Extração em Massa de Transcrições/Legendas das Lives (Streams) - IBPM CR.
Extrai todas as legendas da aba /streams do canal @ibpmcr7976 sem baixar vídeos pesados.
"""

import sys
import os
import re
import json
import csv
import time
import subprocess
from pathlib import Path
from typing import Dict, List, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

# Suporte a UTF-8 nativo no terminal Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from src.core.logger import get_logger
from src.core.state_manager import sanitize_title

logger = get_logger("ExtrairStreams")

# Diretores de Saída
OUTPUT_DIR = BASE_DIR / "dataset_transcricoes" / "streams"
TXT_DIR = OUTPUT_DIR / "txt"
JSON_DIR = OUTPUT_DIR / "json"
COOKIES_FILE = BASE_DIR / "cookies.txt"
PYTHON_EXE = sys.executable

CHANNEL_STREAMS_URL = "https://www.youtube.com/@ibpmcr7976/streams"
MASTER_VIDEOS_JSON = BASE_DIR / "data" / "canal_ibpm_todos_videos.json"


def garantir_diretorios():
    """Garante que as pastas de destino existam."""
    TXT_DIR.mkdir(parents=True, exist_ok=True)
    JSON_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("📁 Pastas de saída preparadas", path=str(OUTPUT_DIR))


def obter_lista_streams() -> List[Dict[str, Any]]:
    """
    Obtém a lista completa de transmissões (streams).
    Primeiro tenta ler do canal_ibpm_todos_videos.json; se incompleto, executa varredura via yt-dlp.
    """
    streams = []
    
    # 1. Tentar ler do JSON cache local se disponível
    if MASTER_VIDEOS_JSON.exists():
        try:
            with open(MASTER_VIDEOS_JSON, "r", encoding="utf-8") as f:
                todos = json.load(f)
                for item in todos:
                    if item.get("source_tab") == "streams" or "live" in item.get("title", "").lower() or "festividade" in item.get("title", "").lower():
                        streams.append({
                            "id": item["id"],
                            "title": item.get("title", f"stream_{item['id']}"),
                            "date": item.get("upload_date", "")
                        })
            logger.info("📋 Vídeos/Streams carregados do cache local", qtd=len(streams))
        except Exception as e:
            logger.warning("Falha ao ler cache local de vídeos", error=str(e))

    # 2. Se trouxer poucas streams, varrer a aba /streams diretamente via yt-dlp
    if len(streams) < 100:
        logger.info("📡 Varrendo a aba /streams do canal no YouTube via yt-dlp...")
        cmd = [
            PYTHON_EXE, "-m", "yt_dlp",
            "--js-runtimes", "node",
            "--flat-playlist",
            "--dump-single-json",
            CHANNEL_STREAMS_URL
        ]
        if COOKIES_FILE.exists():
            cmd.extend(["--cookies", str(COOKIES_FILE)])

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True, encoding="utf-8", errors="replace")
            data = json.loads(res.stdout)
            entries = data.get("entries", [])
            streams_novas = []
            for e in entries:
                if e and e.get("id"):
                    streams_novas.append({
                        "id": e["id"],
                        "title": e.get("title", f"stream_{e['id']}"),
                        "date": e.get("upload_date", "")
                    })
            logger.info("✅ Varredura ao vivo concluída!", total_encontrado=len(streams_novas))
            if len(streams_novas) > len(streams):
                streams = streams_novas
        except Exception as e:
            logger.error("Erro na varredura ao vivo via yt-dlp", error=str(e))

    return streams


def limpar_conteudo_vtt(vtt_text: str) -> str:
    """
    Remove cabeçalhos VTT, timestamps, marcas de formatação e repetições consecutivas.
    """
    lines = vtt_text.splitlines()
    clean_lines = []
    prev_line = ""

    for line in lines:
        line = line.strip()
        # Ignorar linhas de cabeçalho VTT, timestamps, etc.
        if not line or line.startswith("WEBVTT") or line.startswith("Kind:") or line.startswith("Language:"):
            continue
        if "-->" in line:
            continue
        if re.match(r'^\d+$', line):
            continue
        # Limpar tags HTML/VTT como <c>, </c>, <00:01:02.000>
        line = re.sub(r'<[^>]+>', '', line).strip()
        if not line:
            continue
        # Evitar duplicatas consecutivas exatas
        if line != prev_line:
            clean_lines.append(line)
            prev_line = line

    return "\n".join(clean_lines)


def extrair_transcricao_video(item: Dict[str, Any], index: int, total: int) -> Dict[str, Any]:
    """
    Extrai a legenda/transcrição de uma única stream em VTT/JSON e salva em disco.
    """
    video_id = item["id"]
    raw_title = item.get("title", "stream")
    clean_title = sanitize_title(raw_title)
    filename_base = f"{index:03d}_{video_id}_{clean_title}"

    txt_filepath = TXT_DIR / f"{filename_base}.txt"
    json_filepath = JSON_DIR / f"{filename_base}.json"

    # Idempotência: se os arquivos já existem e são maiores que 100 bytes, pula
    if txt_filepath.exists() and txt_filepath.stat().st_size > 100:
        return {
            "index": index,
            "id": video_id,
            "title": raw_title,
            "status": "já_existente",
            "words": len(txt_filepath.read_text(encoding="utf-8", errors="ignore").split())
        }

    temp_out_template = str(OUTPUT_DIR / f"temp_{video_id}.%(ext)s")

    cmd = [
        PYTHON_EXE, "-m", "yt_dlp",
        "--js-runtimes", "node",
        "--write-auto-sub",
        "--write-sub",
        "--sub-lang", "pt,pt-BR,pt-orig",
        "--sub-format", "vtt/json3/best",
        "--skip-download",
        "-o", temp_out_template,
        f"https://www.youtube.com/watch?v={video_id}"
    ]

    if COOKIES_FILE.exists():
        cmd.extend(["--cookies", str(COOKIES_FILE)])

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        
        # Procurar por arquivos temp_{video_id}*.vtt ou *.json3 gerados
        found_sub = None
        for p in OUTPUT_DIR.glob(f"temp_{video_id}*"):
            if p.suffix in [".vtt", ".json3", ".srv3"]:
                found_sub = p
                break

        if not found_sub:
            if "429" in res.stderr or "Too Many Requests" in res.stderr:
                status_str = "bloqueado_ip_429"
            elif "PO Token" in res.stderr:
                status_str = "requer_po_token"
            else:
                status_str = "sem_legenda_natividade"

            return {
                "index": index,
                "id": video_id,
                "title": raw_title,
                "status": status_str,
                "words": 0
            }

        # Ler arquivo de legenda encontrado
        raw_text = found_sub.read_text(encoding="utf-8", errors="ignore")
        clean_text = limpar_conteudo_vtt(raw_text)

        if not clean_text or len(clean_text.strip()) < 20:
            found_sub.unlink(missing_ok=True)
            return {
                "index": index,
                "id": video_id,
                "title": raw_title,
                "status": "legenda_vazia",
                "words": 0
            }

        # Salvar arquivo TXT
        txt_filepath.write_text(clean_text, encoding="utf-8")

        # Salvar arquivo JSON de metadados
        words = len(clean_text.split())
        meta_json = {
            "index": index,
            "video_id": video_id,
            "title": raw_title,
            "url": f"https://www.youtube.com/watch?v={video_id}",
            "word_count": words,
            "line_count": len(clean_text.splitlines()),
            "transcript": clean_text
        }
        json_filepath.write_text(json.dumps(meta_json, ensure_ascii=False, indent=2), encoding="utf-8")

        # Apagar arquivo temporário
        found_sub.unlink(missing_ok=True)

        return {
            "index": index,
            "id": video_id,
            "title": raw_title,
            "status": "sucesso",
            "words": words
        }

    except Exception as e:
        return {
            "index": index,
            "id": video_id,
            "title": raw_title,
            "status": f"erro: {str(e)[:50]}",
            "words": 0
        }


def processar_todas_streams(max_workers: int = 1, delay_sec: float = 2.0):
    """
    Processa todas as streams sequencialmente/com poucas threads, aplicando delay
    entre requisições para respeitar o limite de IP do YouTube (HTTP 429).
    """
    garantir_diretorios()
    streams = obter_lista_streams()
    total = len(streams)

    if not streams:
        logger.error("Nenhuma stream encontrada para processamento.")
        return

    logger.info(f"🚀 Iniciando extração com taxa controlada ({max_workers} thread(s), delay={delay_sec}s per vídeo)...")

    resultados = []
    sucessos = 0
    sem_legenda = 0
    bloqueados_429 = 0
    erros = 0

    if max_workers <= 1:
        # Processamento sequencial seguro com delay
        for i, item in enumerate(streams, 1):
            res = extrair_transcricao_video(item, i, total)
            resultados.append(res)
            status = res["status"]

            if status in ["sucesso", "já_existente"]:
                sucessos += 1
            elif status in ["sem_legenda_natividade", "legenda_vazia", "requer_po_token"]:
                sem_legenda += 1
            elif status == "bloqueado_ip_429":
                bloqueados_429 += 1
                logger.warning(f"⚠️ IP temporariamente limitado pelo YouTube (HTTP 429). Pausando 15s antes da próxima requisição...")
                time.sleep(15.0)
            else:
                erros += 1

            if i % 10 == 0 or i == total:
                logger.info(f"📊 Progresso: {i}/{total} | Sucessos: {sucessos} | Sem legenda/Token: {sem_legenda} | IP 429: {bloqueados_429} | Erros: {erros}")

            if status != "já_existente":
                time.sleep(delay_sec)

    else:
        # Modo multi-threaded
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(extrair_transcricao_video, item, i + 1, total): item
                for i, item in enumerate(streams)
            }

            for future in as_completed(futures):
                res = future.result()
                resultados.append(res)
                status = res["status"]

                if status in ["sucesso", "já_existente"]:
                    sucessos += 1
                elif status in ["sem_legenda_natividade", "legenda_vazia", "requer_po_token"]:
                    sem_legenda += 1
                elif status == "bloqueado_ip_429":
                    bloqueados_429 += 1
                else:
                    erros += 1

                if len(resultados) % 10 == 0 or len(resultados) == total:
                    logger.info(f"📊 Progresso: {len(resultados)}/{total} | Sucessos: {sucessos} | Sem legenda/Token: {sem_legenda} | IP 429: {bloqueados_429} | Erros: {erros}")

    # Ordenar por índice
    resultados.sort(key=lambda x: x["index"])

    # Salvar Relatório CSV
    csv_file = OUTPUT_DIR / "resumo_streams.csv"
    with open(csv_file, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["index", "id", "title", "status", "words"])
        writer.writeheader()
        writer.writerows(resultados)

    logger.info("🎉 Processamento concluído!",
                total=total, sucessos=sucessos, sem_legenda=sem_legenda, bloqueados_429=bloqueados_429, erros=erros, csv=str(csv_file))


if __name__ == "__main__":
    processar_todas_streams(max_workers=1, delay_sec=2.0)

