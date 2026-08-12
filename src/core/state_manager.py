"""
Módulo de Gerenciamento de Estado Idempotente (SQLite + JSON Mestre).

Gerencia a persistência transacional no SQLite local (ibpmcr_master.db),
incluindo a tabela de chunks para busca vetorial RAG e a sincronização do JSON Mestre.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from config.settings import DB_PATH, JSON_MASTER_PATH, DRIVE_ROOT

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MasterPlanManager:
    """
    Gerenciador de Estado do Plano Mestre IBPM CR.
    Garante idempotência (evita reprocessar vídeos já concluídos) e salva os 25 pilares de insights.
    """

    def __init__(self, db_path: str = str(DB_PATH), json_path: str = str(JSON_MASTER_PATH)):
        self.db_path = db_path
        self.json_path = json_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        """Cria a estrutura de tabelas relacionais no SQLite."""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Tabela principal de vídeos com os 25 pilares de insights
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS videos (
                video_id TEXT PRIMARY KEY,
                titulo_original TEXT,
                data_publicacao TEXT,
                duracao_segundos INTEGER,
                visualizacoes INTEGER,
                likes INTEGER,
                quantidade_comentarios INTEGER,
                descricao TEXT,
                url TEXT,
                transcrito INTEGER DEFAULT 0,
                pregador TEXT,
                estilo_homiletico TEXT,
                serie_campanha TEXT,
                referencias_biblicas TEXT,
                proporcao_at_nt TEXT,
                score_viral INTEGER,
                insights_json TEXT,
                created_at TEXT,
                updated_at TEXT
            )
            """)

            # Tabela de Chunks para RAG Teológico / Exegético
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS rag_chunks (
                chunk_id INTEGER PRIMARY KEY AUTOINCREMENT,
                video_id TEXT,
                chunk_index INTEGER,
                start_sec REAL,
                end_sec REAL,
                texto_chunk TEXT,
                tema_predominante TEXT,
                pregador TEXT,
                passagens_biblicas TEXT,
                created_at TEXT,
                FOREIGN KEY (video_id) REFERENCES videos (video_id)
            )
            """)

            conn.commit()
            logger.info(f"✅ Banco de Dados SQLite pronto em: {self.db_path}")

    def is_video_processed(self, video_id: str) -> bool:
        """Verifica se o vídeo já foi analisado com sucesso (Idempotência)."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT transcrito FROM videos WHERE video_id = ? AND transcrito = 1", (video_id,))
            row = cursor.fetchone()
            return row is not None

    def update_video_analysis(self, video_id: str, metadata: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """
        Salva ou atualiza a análise de um vídeo no SQLite com todos os 25 pilares de insights.
        """
        now_str = datetime.now(timezone.utc).isoformat()
        homiletica = analysis.get("homiletica_teologia", {})
        midia = analysis.get("kits_midia_social", {})

        insights_data = {
            "metadata": metadata,
            "analysis": analysis
        }
        insights_json_str = json.dumps(insights_data, ensure_ascii=False)

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
            INSERT INTO videos (
                video_id, titulo_original, data_publicacao, duracao_segundos,
                visualizacoes, likes, quantidade_comentarios, descricao, url,
                transcrito, pregador, estilo_homiletico, serie_campanha,
                referencias_biblicas, proporcao_at_nt, score_viral, insights_json,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(video_id) DO UPDATE SET
                titulo_original=excluded.titulo_original,
                data_publicacao=excluded.data_publicacao,
                duracao_segundos=excluded.duracao_segundos,
                visualizacoes=excluded.visualizacoes,
                likes=excluded.likes,
                quantidade_comentarios=excluded.quantidade_comentarios,
                descricao=excluded.descricao,
                url=excluded.url,
                transcrito=1,
                pregador=excluded.pregador,
                estilo_homiletico=excluded.estilo_homiletico,
                serie_campanha=excluded.serie_campanha,
                referencias_biblicas=excluded.referencias_biblicas,
                proporcao_at_nt=excluded.proporcao_at_nt,
                score_viral=excluded.score_viral,
                insights_json=excluded.insights_json,
                updated_at=excluded.updated_at
            """, (
                video_id,
                metadata.get("titulo_original", ""),
                metadata.get("data_publicacao", ""),
                int(metadata.get("duracao_segundos", 0)),
                int(metadata.get("visualizacoes", 0)),
                int(metadata.get("likes", 0)),
                int(metadata.get("quantidade_comentarios", 0)),
                metadata.get("descricao", ""),
                metadata.get("url", ""),
                homiletica.get("pregador", "Pastor IBPM CR"),
                homiletica.get("estilo_homiletico", "Profética / Exortação"),
                homiletica.get("serie_campanha", "Culto de Altar"),
                ", ".join(homiletica.get("referencias_biblicas", [])),
                json.dumps(homiletica.get("proporcao_at_nt", {"AT": 50, "NT": 50})),
                midia.get("score_potencial_viral", 80),
                insights_json_str,
                now_str,
                now_str
            ))

            # Insere os Chunks RAG
            cursor.execute("DELETE FROM rag_chunks WHERE video_id = ?", (video_id,))
            rag_chunks = analysis.get("rag_chunks_teologicos", [])
            for chunk in rag_chunks:
                cursor.execute("""
                INSERT INTO rag_chunks (video_id, chunk_index, start_sec, end_sec, texto_chunk, tema_predominante, pregador, passagens_biblicas, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    video_id,
                    chunk.get("chunk_index", 1),
                    chunk.get("start_sec", 0.0),
                    chunk.get("end_sec", 30.0),
                    chunk.get("texto_chunk", ""),
                    chunk.get("tema_predominante", "Geral"),
                    chunk.get("pregador", "Pastor IBPM CR"),
                    ", ".join(chunk.get("passagens_biblicas", [])),
                    now_str
                ))

            conn.commit()

        # Atualiza a cópia consolidada em JSON
        self.export_master_json()

    def export_master_json(self) -> str:
        """Exporta todo o estado do banco SQLite para o JSON Mestre."""
        os.makedirs(os.path.dirname(self.json_path), exist_ok=True)
        videos_dict = {}

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT video_id, insights_json FROM videos ORDER BY data_publicacao ASC")
            for row in cursor.fetchall():
                v_id = row["video_id"]
                try:
                    data = json.loads(row["insights_json"])
                    videos_dict[v_id] = data["analysis"]
                    videos_dict[v_id]["metadata"] = data["metadata"]
                except Exception:
                    pass

        master_state = {
            "canal": "@ibpmcr7976",
            "versao_plano_mestre": "2.0-FASE1-25PILARES",
            "total_videos_catalogados": len(videos_dict),
            "ultima_atualizacao": datetime.now(timezone.utc).isoformat(),
            "videos": videos_dict
        }

        with open(self.json_path, "w", encoding="utf-8") as f:
            json.dump(master_state, f, ensure_ascii=False, indent=2)

        # Copia para o Google Drive caso esteja montado
        if os.path.exists(DRIVE_ROOT):
            drive_json = os.path.join(DRIVE_ROOT, "plano_mestre_ibpmcr.json")
            try:
                with open(drive_json, "w", encoding="utf-8") as f:
                    json.dump(master_state, f, ensure_ascii=False, indent=2)
            except Exception as e:
                logger.warning(f"Não foi possível sincronizar com o Drive: {e}")

        logger.info(f"💾 JSON Mestre exportado com sucesso ({len(videos_dict)} vídeos em {self.json_path}).")
        return self.json_path

    def get_all_videos(self) -> List[Dict[str, Any]]:
        """Retorna a lista completa de vídeos catalogados."""
        videos = []
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT insights_json FROM videos ORDER BY data_publicacao ASC")
            for row in cursor.fetchall():
                try:
                    data = json.loads(row["insights_json"])
                    video_entry = data["metadata"]
                    video_entry["analysis"] = data["analysis"]
                    videos.append(video_entry)
                except Exception:
                    pass
        return videos


if __name__ == "__main__":
    mgr = MasterPlanManager()
    print("Estado do Banco SQLite pronto!")
