"""
Módulo de Inteligência Geográfica e Mapas de Calor (GeoPandas / Folium).

Gera mapas espaciais interativos dos pedidos de oração, visitantes e membros cadastrados
na Zona Oeste do Rio de Janeiro (bairros de Campo Grande, Bangu, Santíssimo, Vasconcelos, etc.).
"""

import os
import logging
from typing import List, Dict, Any, Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import get_folder_path

try:
    import folium
    from folium.plugins import HeatMap
    HAS_FOLIUM = True
except ImportError:
    HAS_FOLIUM = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Coordenadas de referência da IBPM CR em Campo Grande (Rua Ajurana, 510)
CAMPO_GRANDE_LAT_LON = [-22.9035, -43.5592]


class SpatialGeoAnalytics:
    """
    Gerador de mapas de calor para assistência pastoral e evangelismo espacial.
    """

    def __init__(self):
        """
        Inicializa o diretório de relatórios de analytics.
        """
        self.output_dir = get_folder_path("RELATORIOS_ANALYTICS")
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_prayer_heatmap(
        self,
        locations: Optional[List[Dict[str, Any]]] = None,
        output_filename: str = "mapa_calor_pedidos_oracao.html"
    ) -> str:
        """
        Gera um mapa de calor interativo com Folium focado na Zona Oeste do RJ.

        :param locations: Lista de coordenadas [{'lat': float, 'lon': float, 'weight': int, 'bairro': str}].
        :param output_filename: Nome do arquivo HTML de saída.
        :return: Caminho do arquivo HTML salvo.
        """
        output_path = os.path.join(self.output_dir, output_filename)
        logger.info("🗺️ Gerando Mapa de Calor Espacial com Folium...")

        if not locations:
            locations = self._get_sample_locations()

        if not HAS_FOLIUM:
            logger.warning("⚠️ Folium não está instalado. Salvando arquivo HTML estático de fallback.")
            return self._save_mock_html(output_path)

        try:
            # Inicializa o mapa centralizado em Campo Grande, RJ
            m = folium.Map(location=CAMPO_GRANDE_LAT_LON, zoom_start=13, tiles="OpenStreetMap")

            # Marcador da Sede da Igreja
            folium.Marker(
                location=CAMPO_GRANDE_LAT_LON,
                popup="<b>IBPM CR - Sede Matriz</b><br>Rua Ajurana, 510 - Campo Grande",
                icon=folium.Icon(color="red", icon="home", prefix="fa")
            ).add_to(m)

            # Prepara dados para a camada de calor
            heat_data = [[item["lat"], item["lon"], item.get("weight", 1)] for item in locations]
            HeatMap(heat_data, radius=18, blur=12).add_to(m)

            # Adiciona marcadores de bairros
            for loc in locations:
                folium.CircleMarker(
                    location=[loc["lat"], loc["lon"]],
                    radius=5,
                    popup=f"Bairro: {loc.get('bairro', 'Zona Oeste')}<br>Pedidos: {loc.get('weight', 1)}",
                    color="blue",
                    fill=True
                ).add_to(m)

            m.save(output_path)
            logger.info(f"✅ Mapa de calor salvo com sucesso: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"❌ Erro ao gerar mapa com Folium: {e}")
            return self._save_mock_html(output_path)

    def _get_sample_locations(self) -> List[Dict[str, Any]]:
        """Amostras de coordenadas nos bairros da Zona Oeste RJ próximos à IBPM CR."""
        return [
            {"lat": -22.9035, "lon": -43.5592, "weight": 15, "bairro": "Campo Grande Center"},
            {"lat": -22.8980, "lon": -43.5450, "weight": 8, "bairro": "Senador Vasconcelos"},
            {"lat": -22.8850, "lon": -43.5200, "weight": 10, "bairro": "Santíssimo"},
            {"lat": -22.8750, "lon": -43.4650, "weight": 12, "bairro": "Bangu"},
            {"lat": -22.9150, "lon": -43.5780, "weight": 6, "bairro": "Inhoaíba"}
        ]

    def _save_mock_html(self, output_path: str) -> str:
        html_content = (
            "<html><head><title>Mapa IBPM CR</title></head><body>"
            "<h2>Mapa de Calor - Zona Oeste RJ (Campo Grande)</h2>"
            "<p>Centralizado na Rua Ajurana, 510. Exibição interativa via Streamlit.</p>"
            "</body></html>"
        )
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return output_path


if __name__ == "__main__":
    geo = SpatialGeoAnalytics()
    map_file = geo.generate_prayer_heatmap()
    print(f"Mapa gerado em: {map_file}")
