"""
Gerenciador de Estado do Banco de Dados SQLite Relacional (Etapa 1 - IBPM CR).

Gerencia o inventário relacional de vídeos, salvando o índice sequencial (001 a 447+),
a nomenclatura sanitizada dos arquivos MP3 e o controle de idempotência do download.
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
    """
    Sanitiza o título do vídeo para uso em nomes de arquivo seguros no SO:
    Remove acentos, caracteres especiais e espaços excessivos, mantendo apenas a-z, 0-9 e underline.
    """
    if not title:
        return "culto_ibpmcr"
    
    # Normaliza unicode NFD (separa acentos dos caracteres)
    nfkd = unicodedata.normalize('NFKD', title)
    no_accents = "".join([c for c in nfkd if not unicodedata.combining(c)])
    
    # Converte para minúsculas e substitui caracteres não alfanuméricos por underline
    clean = re.sub(r'[^a-zA-Z0-9]+', '_', no_accents.lower()).strip('_')
    
    # Limita tamanho para evitar caminhos longos demais no Windows
    return clean[:60] if clean else "culto_ibpmcr"


class MasterPlanManager:
    """
    Gerenciador do Banco de Dados SQLite Relacional para o ecossistema IBPM CR.
    """

    def __init__(self, db_path: str = str(DB_PATH)):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria e atualiza a estrutura de tabelas relacionais no SQLite."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabela principal de vídeos
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
                pregador TEXT,
                estilo_homiletico TEXT,
                serie_campanha TEXT,
                referencias_biblicas TEXT,
                proporcao_at_nt TEXT,
                score_viral INTEGER DEFAULT 0,
                insights_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            # Garante colunas caso a tabela já existisse
            for col_def in [
                ("indice_sequencial", "INTEGER"),
                ("nome_arquivo_mp3", "TEXT"),
                ("titulo_sanitizado", "TEXT"),
                ("audio_baixado", "INTEGER DEFAULT 0"),
                ("caminho_audio", "TEXT"),
                ("transcrito", "INTEGER DEFAULT 0"),
                ("texto_transcrito", "TEXT"),
                ("segmentos_json", "TEXT"),
                ("tipo_transcricao", "TEXT DEFAULT 'pendente'"),
                ("analisado_pln", "INTEGER DEFAULT 0")
            ]:
                try:
                    cursor.execute(f"ALTER TABLE videos ADD COLUMN {col_def[0]} {col_def[1]};")
                except Exception:
                    pass

            conn.commit()

    def save_video_metadata(self, metadata: Dict[str, Any]) -> None:
        """Salva ou atualiza os metadados do vídeo com índice sequencial e nome de arquivo MP3."""
        v_id = metadata["video_id"]
        idx = metadata.get("indice_sequencial", 0)
        now_str = datetime.now(timezone.utc).isoformat()

        date_str = str(metadata.get("data_publicacao", ""))[:10]
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
                v_id,
                idx,
                filename_mp3,
                metadata.get("titulo_original", ""),
                clean_title,
                metadata.get("data_publicacao", ""),
                metadata.get("duracao_segundos", 0),
                metadata.get("visualizacoes", 0),
                metadata.get("likes", 0),
                metadata.get("quantidade_comentarios", 0),
                metadata.get("descricao", ""),
                metadata.get("url", f"https://www.youtube.com/watch?v={v_id}"),
                now_str,
                now_str
            ))
            conn.commit()

    def mark_audio_downloaded(self, video_id: str, audio_path: str) -> None:
        """Marca o áudio como baixado no SQLite e grava o caminho completo do arquivo."""
        now_str = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            UPDATE videos SET audio_baixado = 1, caminho_audio = ?, updated_at = ? WHERE video_id = ?
            """, (audio_path, now_str, video_id))
            conn.commit()

    def is_audio_downloaded(self, video_id: str) -> bool:
        """Checa no SQLite e no sistema de arquivos se o áudio já foi baixado (Idempotência)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT audio_baixado, caminho_audio FROM videos WHERE video_id = ?", (video_id,))
            row = cursor.fetchone()

            if row and row["audio_baixado"] == 1 and row["caminho_audio"]:
                if os.path.exists(row["caminho_audio"]) and os.path.getsize(row["caminho_audio"]) > 10000:
                    return True

        # Verifica na pasta audio_podcasts se existe algum arquivo com aquele video_id no nome
        if os.path.exists(AUDIO_DIR):
            for fname in os.listdir(AUDIO_DIR):
                if video_id in fname:
                    full_p = os.path.join(AUDIO_DIR, fname)
                    if os.path.getsize(full_p) > 10000:
                        self.mark_audio_downloaded(video_id, full_p)
                        return True
        return False

    def get_all_videos_chronological(self) -> List[Dict[str, Any]]:
        """Retorna todos os vídeos cadastrados ordenados por indice_sequencial."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM videos ORDER BY indice_sequencial ASC")
            return [dict(r) for r in cursor.fetchall()]


if __name__ == "__main__":
    mgr = MasterPlanManager()
    print("MasterPlanManager (Etapa 1) pronto!")
