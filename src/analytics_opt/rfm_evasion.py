"""
Modelo Preditivo de Evasão Pastoral e Análise RFM (scikit-learn).

Aplica Machine Learning (Clustering KMeans) sobre a métrica RFM (Recência, Frequência e Engajamento)
para identificar membros ou visitantes em risco de afastamento da comunidade.
"""

import logging
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))

try:
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class PastoralEvasionRFMModel:
    """
    Modelo de Machine Learning para retenção comunitária e cuidado pastoral proativo.
    """

    def __init__(self, n_clusters: int = 3):
        """
        Inicializa o modelo de agrupação RFM.

        :param n_clusters: Número de clusters (Ex: 0=Engajados, 1=Atenção, 2=Risco de Evasão).
        """
        self.n_clusters = n_clusters
        self.scaler = StandardScaler() if HAS_SKLEARN else None
        self.kmeans = KMeans(n_clusters=n_clusters, random_state=42) if HAS_SKLEARN else None

    def analyze_member_retention(self, member_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Analisa o padrão de frequência e engajamento dos membros.

        :param member_records: Lista de registros [{'id': int, 'name': str, 'recency_days': int, 'frequency_services': int, 'engagement_score': float}].
        :return: Relatório com alertas de cuidado pastoral.
        """
        logger.info(f"📈 Analisando dados de retenção pastoral para {len(member_records)} registros...")

        if not member_records:
            return {"alerts": [], "summary": "Sem dados suficientes."}

        df = pd.DataFrame(member_records)

        if HAS_SKLEARN and len(df) >= self.n_clusters:
            try:
                features = df[["recency_days", "frequency_services", "engagement_score"]]
                scaled_features = self.scaler.fit_transform(features)
                df["cluster"] = self.kmeans.fit_predict(scaled_features)

                # Identifica cluster de maior recência e menor frequência como alto risco
                risk_cluster_id = df.groupby("cluster")["recency_days"].mean().idxmax()
                df["is_at_risk"] = df["cluster"] == risk_cluster_id
            except Exception as e:
                logger.warning(f"Erro no agrupamento KMeans: {e}. Usando regra empírica.")
                df["is_at_risk"] = (df["recency_days"] > 21) | (df["frequency_services"] <= 1)
        else:
            # Regra empírica: ausência > 21 dias (3 semanas)
            df["is_at_risk"] = (df["recency_days"] > 21) | (df["frequency_services"] <= 1)

        at_risk_members = df[df["is_at_risk"]].to_dict(orient="records")

        logger.info(f"⚠️ {len(at_risk_members)} membros identificados em risco de afastamento.")

        return {
            "total_analyzed": len(df),
            "at_risk_count": len(at_risk_members),
            "at_risk_members": [
                {
                    "name": m.get("name"),
                    "recency_days": m.get("recency_days"),
                    "frequency_services": m.get("frequency_services"),
                    "pastoral_action": "Agendar visita domiciliar ou mensagem carinhosa de acolhimento"
                }
                for m in at_risk_members
            ]
        }


if __name__ == "__main__":
    rfm = PastoralEvasionRFMModel()
    sample_records = [
        {"id": 1, "name": "Irmão Pedro", "recency_days": 3, "frequency_services": 8, "engagement_score": 9.5},
        {"id": 2, "name": "Irmã Cláudia", "recency_days": 28, "frequency_services": 1, "engagement_score": 2.0},
        {"id": 3, "name": "Jovem Roberto", "recency_days": 7, "frequency_services": 4, "engagement_score": 7.0}
    ]
    res = rfm.analyze_member_retention(sample_records)
    print("Alertas de Evasão Pastoral:")
    print(res)
