"""
Gerenciador do Plano Mestre de Mídia (plano_mestre_ibpmcr.json e SQLite).

Registra o estado de todo o acervo histórico do canal IBPM CR (@ibpmcr7976),
gerenciando o plano mestre no Google Drive com persistência dupla em JSON e SQLite.
"""

import os
import json
import sqlite3
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import OUTPUT_BASE_DIR, SUBFOLDERS

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class MasterPlanManager:
    """
    Gerenciador centralizado do Plano Mestre de Mídia da IBPM CR (JSON + SQLite).
    """

    def __init__(self, drive_path: Optional[str] = None):
        """
        Inicializa os arquivos de persistência do Plano Mestre.

        :param drive_path: Caminho customizado para salvamento no Google Drive.
        """
        self.base_dir = drive_path or OUTPUT_BASE_DIR
        os.makedirs(self.base_dir, exist_ok=True)

        self.json_path = os.path.join(self.base_dir, "plano_mestre_ibpmcr.json")
        self.db_path = os.path.join(self.base_dir, "plano_mestre_ibpmcr.db")

        self._init_sqlite_db()
        self.state: Dict[str, Any] = self._load_json_state()

    def _init_sqlite_db(self) -> None:
        """Inicializa as tabelas do banco SQLite para o Plano Mestre."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS videos_master (
                    video_id TEXT PRIMARY KEY,
                    titulo_original TEXT,
                    data_publicacao TEXT,
                    duracao_segundos INTEGER,
                    visualizacoes INTEGER,
                    likes INTEGER,
                    quantidade_comentarios INTEGER,
                    descricao TEXT,
                    transcrito INTEGER DEFAULT 0,
                    potencial_ebook INTEGER DEFAULT 0,
                    potencial_kids INTEGER DEFAULT 0,
                    tema_principal TEXT,
                    plano_cortes_json TEXT,
                    criado_em TEXT
                )
            """)
            conn.commit()
            conn.close()
            logger.info(f"✅ Banco SQLite do Plano Mestre pronto em: {self.db_path}")
        except Exception as e:
            logger.error(f"❌ Erro ao inicializar banco SQLite: {e}")

    def _load_json_state(self) -> Dict[str, Any]:
        """Carrega o arquivo plano_mestre_ibpmcr.json do Drive."""
        if os.path.exists(self.json_path):
            try:
                with open(self.json_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Erro ao ler JSON {self.json_path}: {e}")
                return self._default_master_plan()
        return self._default_master_plan()

    def _default_master_plan(self) -> Dict[str, Any]:
        """Estrutura padrão do Plano Mestre de Mídia."""
        return {
            "canal": "@ibpmcr7976",
            "versao_plano_mestre": "1.0-FASE1",
            "ultima_atualizacao": datetime.now(timezone.utc).isoformat(),
            "videos": {},
            "filas": {
                "recentes_48h": [],
                "mais_vistos": [],
                "acervo_historico": []
            }
        }

    def save_master_plan(self) -> None:
        """Persiste o estado atualizado em JSON e SQLite no Google Drive."""
        try:
            self.state["ultima_atualizacao"] = datetime.now(timezone.utc).isoformat()
            
            # 1. Salva em JSON
            with open(self.json_path, "w", encoding="utf-8") as f:
                json.dump(self.state, f, ensure_ascii=False, indent=2)

            # 2. Salva / Sincroniza em SQLite
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            for vid, data in self.state["videos"].items():
                cursor.execute("""
                    INSERT OR REPLACE INTO videos_master (
                        video_id, titulo_original, data_publicacao, duracao_segundos,
                        visualizacoes, likes, quantidade_comentarios, descricao,
                        transcrito, potencial_ebook, potencial_kids, tema_principal,
                        plano_cortes_json, criado_em
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    vid,
                    data.get("titulo_original", ""),
                    data.get("data_publicacao", ""),
                    data.get("duracao_segundos", 0),
                    data.get("visualizacoes", 0),
                    data.get("likes", 0),
                    data.get("quantidade_comentarios", 0),
                    data.get("descricao", ""),
                    1 if data.get("transcrito") else 0,
                    1 if data.get("potencial_ebook_devocional", {}).get("apropriado_para_ebook") else 0,
                    1 if data.get("potencial_ebd_kids", {}).get("apropriado_para_ebd_kids") else 0,
                    data.get("tema_principal", "Geral"),
                    json.dumps(data.get("mapa_cortes", {}), ensure_ascii=False),
                    datetime.now(timezone.utc).isoformat()
                ))

            conn.commit()
            conn.close()
            logger.info("💾 Plano Mestre salvo com sucesso (plano_mestre_ibpmcr.json & SQLite).")

        except Exception as e:
            logger.error(f"❌ Erro ao salvar Plano Mestre: {e}")

    def update_video_analysis(self, video_id: str, meta: Dict[str, Any], analysis: Dict[str, Any]) -> None:
        """
        Atualiza os dados de varredura e mapa de cortes para um vídeo específico.

        :param video_id: ID do vídeo no YouTube.
        :param meta: Metadados extraídos pelo sweeper.
        :param analysis: Mapa de minutagens extraídos pelo content_analyzer.
        """
        if video_id not in self.state["videos"]:
            self.state["videos"][video_id] = meta

        self.state["videos"][video_id].update({
            "transcrito": True,
            "potencial_cortes_curtos_9_16": analysis.get("potencial_cortes_curtos_9_16", []),
            "potencial_cortes_medios_16_9": analysis.get("potencial_cortes_medios_16_9", {}),
            "potencial_ebook_devocional": analysis.get("potencial_ebook_devocional", {}),
            "potencial_ebd_kids": analysis.get("potencial_ebd_kids", {}),
            "louvores_executados_bloco": analysis.get("louvores_executados_bloco", {})
        })

        self.save_master_plan()

    def get_summary(self) -> Dict[str, Any]:
        """Estatísticas consolidadas do Plano Mestre."""
        total = len(self.state["videos"])
        transcribed = sum(1 for v in self.state["videos"].values() if v.get("transcrito"))
        ebooks = sum(1 for v in self.state["videos"].values() if v.get("potencial_ebook_devocional", {}).get("apropriado_para_ebook"))
        kids = sum(1 for v in self.state["videos"].values() if v.get("potencial_ebd_kids", {}).get("apropriado_para_ebd_kids"))

        return {
            "total_videos_mapeados": total,
            "videos_transcritos": transcribed,
            "potencial_ebooks": ebooks,
            "potencial_kids": kids,
            "json_path": self.json_path,
            "sqlite_path": self.db_path
        }


# Mantém compatibilidade com StateManager
StateManager = MasterPlanManager


if __name__ == "__main__":
    mp = MasterPlanManager()
    print("Plano Mestre Inicializado:")
    print(mp.get_summary())
