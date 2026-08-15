"""
Script de Mapeamento, Renomeação e Auditoria de Transcrições - IBPM CR Automation System.

Resolve a divergência entre a ordem do YouTube (2026 -> 2022) e os arquivos de áudio locais (001 em 2022 -> 448 em 2026):
1. Mapeia as transcrições baixadas via ID do Vídeo do YouTube.
2. Renomeia os arquivos de transcrição (.txt e .json) em data/audio_podcasts/transcricoes_fase2/
   para terem O MESMO NOME EXATO do arquivo de áudio local (ex: 001_2022-10-03_2hvx5L2DR2U_...).
3. Gera o arquivo 'data/lista_audios_sem_transcricao.txt' contendo a lista EXATA dos 80 áudios
   que NÃO têm legenda no YouTube e que precisam ser transcritos no Whisper.
"""

import sys
import os
import re
import json
from pathlib import Path
from typing import Dict, List, Any, Optional

BASE_DIR = Path(__file__).resolve().parent
sys.path.append(str(BASE_DIR))

# Suporte UTF-8 no console do Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from src.core.logger import get_logger

logger = get_logger("AuditoriaTranscricoes")


def extract_video_id(filename: str) -> Optional[str]:
    """Extrai o ID de 11 caracteres do YouTube do nome do arquivo."""
    match = re.search(r'_([a-zA-Z0-9_-]{11})_', filename)
    if match:
        return match.group(1)
    return None


def auditar_e_sincronizar_transcricoes():
    audio_dir = Path("data/audio_podcasts")
    trans_dir = Path("data/audio_podcasts/transcricoes_fase2")
    relatorio_txt = Path("data/relatorio_auditoria_transcricoes.txt")
    sem_transcricao_txt = Path("data/lista_audios_sem_transcricao.txt")

    if not audio_dir.exists():
        logger.error(f"Pasta de áudios '{audio_dir}' não encontrada!")
        return

    trans_dir.mkdir(parents=True, exist_ok=True)

    # 1. Mapeia todos os arquivos de áudio locais por ID do Vídeo
    audio_files: List[Path] = []
    for ext in [".webm", ".mp4", ".m4a", ".mp3"]:
        audio_files.extend(audio_dir.glob(f"*{ext}"))

    audio_files = sorted(audio_files, key=lambda p: p.name)
    audio_id_map: Dict[str, Path] = {}
    for af in audio_files:
        vid = extract_video_id(af.name)
        if vid:
            audio_id_map[vid] = af

    logger.info(f"{len(audio_files)} arquivos de áudio locais encontrados em '{audio_dir}'.")

    # 2. Mapeia todas as transcrições existentes por ID do Vídeo (lendo o JSON ou buscando no nome)
    trans_json_files = list(trans_dir.glob("*.json"))
    trans_id_map: Dict[str, tuple[Path, Optional[Path]]] = {}

    for jf in trans_json_files:
        tf = jf.with_suffix(".txt")
        vid = None
        try:
            with open(jf, "r", encoding="utf-8") as f:
                data = json.load(f)
                vid = data.get("video_id")
        except Exception:
            vid = extract_video_id(jf.name)

        if not vid:
            vid = extract_video_id(jf.name)

        if vid:
            trans_id_map[vid] = (jf, tf if tf.exists() else None)

    logger.info(f"{len(trans_id_map)} transcrições encontradas na pasta '{trans_dir}'.")

    # 3. Renomeia as transcrições para baterem EXATAMENTE com o nome do arquivo local de áudio
    renomeados_count = 0
    encontrados = []
    faltantes = []

    for af in audio_files:
        vid = extract_video_id(af.name)
        stem = af.stem
        target_json = trans_dir / f"{stem}.json"
        target_txt = trans_dir / f"{stem}.txt"

        if vid and vid in trans_id_map:
            jf_old, tf_old = trans_id_map[vid]

            # Substitui de forma segura o JSON
            if jf_old.name != target_json.name and jf_old.exists():
                jf_old.replace(target_json)

            # Substitui de forma segura o TXT
            if tf_old and tf_old.name != target_txt.name and tf_old.exists():
                tf_old.replace(target_txt)

            renomeados_count += 1
            encontrados.append(af)
        else:
            faltantes.append(af)

    # 4. Escreve a lista exata dos áudios que NÃO possuem transcrição
    with open(sem_transcricao_txt, "w", encoding="utf-8") as f:
        f.write("# LISTA DE ÁUDIOS QUE NÃO POSSUEM TRANSCRIÇÃO NO YOUTUBE (NECESSITAM WHISPER LOCAL)\n")
        for af in faltantes:
            f.write(f"{af.name}\n")

    # 5. Escreve o relatório detalhado de auditoria
    with open(relatorio_txt, "w", encoding="utf-8") as f:
        f.write("================================================================================\n")
        f.write("         IBPM CR - RELATÓRIO DE AUDITORIA E SINCRONIZAÇÃO DE TRANSCRIÇÕES        \n")
        f.write("================================================================================\n\n")
        f.write(f"• Total de áudios no acervo local: {len(audio_files)}\n")
        f.write(f"• Áudios COM transcrição pronta (poupou Whisper): {len(encontrados)}\n")
        f.write(f"• Áudios PENDENTES de transcrição (rodar Whisper local): {len(faltantes)}\n\n")
        f.write("--------------------------------------------------------------------------------\n")
        f.write("STATUS INDIVIDUAL DE CADA CULTO:\n")
        f.write("--------------------------------------------------------------------------------\n")
        for af in audio_files:
            vid = extract_video_id(af.name)
            has_trans = vid and vid in trans_id_map
            status_str = "[OK] COM TRANSCRIÇÃO" if has_trans else "[PENDENTE] RODAR WHISPER"
            f.write(f"{af.name} -> {status_str}\n")

    print("\n" + "=" * 65)
    print(" SINCRONIZACAO E AUDITORIA DE TRANSCRIÇÕES CONCLUÍDA!")
    print(f" * Total de áudios locais: {len(audio_files)}")
    print(f" * Transcrições sincronizadas/renomeadas com sucesso: {renomeados_count}")
    print(f" * Áudios pendentes sem legenda no YouTube: {len(faltantes)}")
    print(f" * Lista para o Whisper gerada em: '{sem_transcricao_txt}'")
    print(f" * Relatório de auditoria salvo em: '{relatorio_txt}'")
    print("=" * 65 + "\n")


if __name__ == "__main__":
    auditar_e_sincronizar_transcricoes()
