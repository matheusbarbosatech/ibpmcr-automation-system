"""
Gerenciador de Estado do Banco de Dados SQLite Relacional (Etapa 1 e Etapa 2 Mineração - IBPM CR).

Gerencia o inventário relacional de vídeos, salvando o índice sequencial (001 a 447+),
status de download, transcrições e o acervo de insights minerados pela IA (Fase 2 Mineração).
"""

import os
import re
import json
import sqlite3
import unicodedata
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import DB_PATH, AUDIO_DIR

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("StateManager")


def sanitize_title(title: str) -> str:
    if not title:
        return "culto_ibpmcr"
    
    nfkd = unicodedata.normalize('NFKD', title)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', no_accents.lower()).strip('_')
    return clean[:60] if clean else "culto_ibpmcr"


class MasterPlanManager:
    """
    Gerenciador do Banco de Dados SQLite Relacional para o ecossistema IBPM CR.
    """

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria e atualiza a estrutura de tabelas relacionais no SQLite."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabela Master de Vídeos
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                indice_sequencial INTEGER,
                nome_arquivo_mp3 TEXT,
                titulo_original TEXT,
                titulo_sanitizado TEXT,
                data_publicacao TEXT,
                duracao_segundos INTEGER DEFAULT 0,
                visualizacoes INTEGER DEFAULT 0,
                likes INTEGER DEFAULT 0,
                quantidade_comentarios INTEGER DEFAULT 0,
                descricao TEXT,
                url TEXT,
                audio_baixado INTEGER DEFAULT 0,
                caminho_audio TEXT,
                transcrito INTEGER DEFAULT 0,
                texto_transcrito TEXT,
                segmentos_json TEXT,
                tipo_transcricao TEXT DEFAULT 'pendente',
                analisado_pln INTEGER DEFAULT 0,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            # Tabela da Fase 2 Mineração: Acervo de Insights Minerados
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS acervo_insights (
                video_id TEXT PRIMARY KEY,
                indice_sequencial INTEGER,
                titulo_original TEXT,
                tema_central TEXT,
                frases_virais TEXT,
                passagens_biblicas TEXT,
                ideia_carrossel_instagram TEXT,
                cortes_virais TEXT,
                prompt_thumbnail TEXT,
                raw_json_response TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            conn.commit()

    def save_video_metadata(self, metadata: Dict[str, Any]) -> None:
        v_id = metadata["video_id"]
        idx = metadata.get("indice_sequencial", 0)
        now_str = datetime.now(timezone.utc).isoformat()

        date_str = str(metadata.get("data_evento_real", metadata.get("data_publicacao", "")))[:10]
        clean_title = sanitize_title(metadata.get("titulo_original", ""))
        filename_mp3 = f"{idx:03d}_{date_str}_{v_id}_{clean_title}.mp3"

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO videos (
                video_id, indice_sequencial, nome_arquivo_mp3, titulo_original,
                titulo_sanitizado, data_publicacao, duracao_segundos, visualizacoes,
                likes, quantidade_comentarios, descricao, url, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                indice_sequencial=excluded.indice_sequencial,
                nome_arquivo_mp3=excluded.nome_arquivo_mp3,
                titulo_original=excluded.titulo_original,
                titulo_sanitizado=excluded.titulo_sanitizado,
                data_publicacao=excluded.data_publicacao,
                duracao_segundos=excluded.duracao_segundos,
                visualizacoes=excluded.visualizacoes,
                likes=excluded.likes,
                quantidade_comentarios=excluded.quantidade_comentarios,
                descricao=excluded.descricao,
                url=excluded.url,
                updated_at=excluded.updated_at
            """, (
                v_id, idx, filename_mp3, metadata.get("titulo_original", ""), clean_title,
                metadata.get("data_publicacao", ""), metadata.get("duracao_segundos", 0),
                metadata.get("visualizacoes", 0), metadata.get("likes", 0),
                metadata.get("quantidade_comentarios", 0), metadata.get("descricao", ""),
                metadata.get("url", f"https://www.youtube.com/watch?v={v_id}"),
                now_str, now_str
            ))
            conn.commit()

    def mark_audio_downloaded(self, video_id: str, audio_path: str) -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE videos SET audio_baixado = 1, caminho_audio = ?, updated_at = ? WHERE video_id = ?", (audio_path, now_str, video_id))
            conn.commit()

    def save_transcription_result(self, video_id: str, full_text: str, segments_json: str, tipo_transcricao: str = "concluida") -> None:
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE videos SET transcrito = 1, texto_transcrito = ?, segmentos_json = ?, tipo_transcricao = ?, updated_at = ? WHERE video_id = ?
            """, (full_text, segments_json, tipo_transcricao, now_str, video_id))
            conn.commit()

    def save_insights_fase2(self, video_id: str, idx: int, title: str, insights_dict: Dict[str, Any], raw_json: str) -> None:
        """Salva os insights estruturados extraídos pelo LLM na tabela acervo_insights (Fase 2 Mineração)."""
        now_str = datetime.now(timezone.utc).isoformat()
        
        tema = str(insights_dict.get("01_tema_central", ""))
        frases = json.dumps(insights_dict.get("02_frases_virais", []), ensure_ascii=False)
        passagens = json.dumps(insights_dict.get("03_passagens_biblicas", []), ensure_ascii=False)
        carrossel = json.dumps(insights_dict.get("04_ideia_carrossel_instagram", []), ensure_ascii=False)
        cortes = json.dumps(insights_dict.get("05_cortes_virais", []), ensure_ascii=False)
        prompt_thumb = str(insights_dict.get("06_prompt_thumbnail", ""))

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO acervo_insights (
                video_id, indice_sequencial, titulo_original, tema_central,
                frases_virais, passagens_biblicas, ideia_carrossel_instagram,
                cortes_virais, prompt_thumbnail, raw_json_response, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                indice_sequencial=excluded.indice_sequencial,
                titulo_original=excluded.titulo_original,
                tema_central=excluded.tema_central,
                frases_virais=excluded.frases_virais,
                passagens_biblicas=excluded.passagens_biblicas,
                ideia_carrossel_instagram=excluded.ideia_carrossel_instagram,
                cortes_virais=excluded.cortes_virais,
                prompt_thumbnail=excluded.prompt_thumbnail,
                raw_json_response=excluded.raw_json_response,
                updated_at=excluded.updated_at
            """, (
                video_id, idx, title, tema, frases, passagens, carrossel, cortes, prompt_thumb, raw_json, now_str, now_str
            ))
            
            # Marca analisado_pln = 1 na tabela videos
            cursor.execute("UPDATE videos SET analisado_pln = 1, updated_at = ? WHERE video_id = ?", (now_str, video_id))
            conn.commit()

    save_insights_fase3 = save_insights_fase2

    def is_insight_processed(self, video_id: str) -> bool:
        """Verifica se o vídeo já possui relatório na tabela acervo_insights."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT video_id FROM acervo_insights WHERE video_id = ?", (video_id,))
            return cursor.fetchone() is not None

    def is_transcribed(self, video_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT transcrito, texto_transcrito FROM videos WHERE video_id = ?", (video_id,))
            row = cursor.fetchone()
            return bool(row and row["transcrito"] == 1 and row["texto_transcrito"] and len(row["texto_transcrito"].strip()) > 50)

    def is_audio_downloaded(self, video_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT audio_baixado, caminho_audio FROM videos WHERE video_id = ?", (video_id,))
            row = cursor.fetchone()
            if row and row["audio_baixado"] == 1 and row["caminho_audio"]:
                if os.path.exists(row["caminho_audio"]) and os.path.getsize(row["caminho_audio"]) > 10000:
                    return True
        return False

    def get_all_videos_chronological(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY indice_sequencial ASC")
            return [dict(r) for r in cursor.fetchall()]


if __name__ == "__main__":
    mgr = MasterPlanManager()
    print("MasterPlanManager atualizado com a tabela acervo_insights da Fase 3!")
