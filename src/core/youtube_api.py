"""
Integração com YouTube Data API v3.

Fornece funções para buscar transmissões ao vivo e vídeos gravados do canal @ibpmcr7976,
gerenciar a ordenação por visualizações/datas e extrair comentários para análise de sentimento.
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, timezone
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_HANDLE, YOUTUBE_CHANNEL_ID

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class YouTubeAPIClient:
    """
    Cliente da YouTube Data API v3 para o canal da IBPM CR (@ibpmcr7976).
    """

    def __init__(self, api_key: Optional[str] = None):
        """
        Inicializa o cliente da API do YouTube.

        :param api_key: Chave da API v3 do YouTube Data API.
        """
        self.api_key = api_key or YOUTUBE_API_KEY
        self.youtube = None

        if self.api_key and HAS_GOOGLE_API:
            try:
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                logger.info("✅ YouTube Data API v3 inicializado com sucesso.")
            except Exception as e:
                logger.warning(f"⚠️ Não foi possível inicializar a API do YouTube: {e}. Entrando em modo mock/fallback.")
        else:
            logger.warning("⚠️ Chave de API do YouTube não fornecida ou google-api-python-client ausente. Usando modo mock.")

    def fetch_recent_videos(self, hours: int = 48) -> List[Dict[str, Any]]:
        """
        Busca os vídeos publicados nas últimas `hours` horas (Fila 1).

        :param hours: Janela de horas (padrão 48h).
        :return: Lista de dicionários com metadados dos vídeos.
        """
        if not self.youtube:
            return self._mock_recent_videos()

        try:
            published_after = (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()
            search_response = self.youtube.search().list(
                q="",
                channelId=YOUTUBE_CHANNEL_ID,
                part="id,snippet",
                order="date",
                publishedAfter=published_after,
                maxResults=20,
                type="video"
            ).execute()

            videos = []
            for item in search_response.get("items", []):
                vid_id = item["id"]["videoId"]
                snippet = item["snippet"]
                videos.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "published_at": snippet["publishedAt"],
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "view_count": self._get_video_view_count(vid_id)
                })

            logger.info(f"Fila 1 (Recentes 48h): {len(videos)} vídeos encontrados via API.")
            return videos

        except Exception as e:
            logger.error(f"Erro ao buscar vídeos recentes via API: {e}. Usando dados simulados.")
            return self._mock_recent_videos()

    def fetch_most_viewed_videos(self, max_results: int = 50) -> List[Dict[str, Any]]:
        """
        Busca os vídeos mais vistos do canal ordenados por viewCount (Fila 2).

        :param max_results: Quantidade máxima de vídeos.
        :return: Lista de vídeos ordenados por popularidade.
        """
        if not self.youtube:
            return self._mock_most_viewed_videos()

        try:
            search_response = self.youtube.search().list(
                channelId=YOUTUBE_CHANNEL_ID,
                part="id,snippet",
                order="viewCount",
                maxResults=max_results,
                type="video"
            ).execute()

            videos = []
            for item in search_response.get("items", []):
                vid_id = item["id"]["videoId"]
                snippet = item["snippet"]
                videos.append({
                    "video_id": vid_id,
                    "title": snippet["title"],
                    "published_at": snippet["publishedAt"],
                    "url": f"https://www.youtube.com/watch?v={vid_id}",
                    "view_count": self._get_video_view_count(vid_id)
                })

            logger.info(f"Fila 2 (Mais Vistos): {len(videos)} vídeos encontrados via API.")
            return videos

        except Exception as e:
            logger.error(f"Erro ao buscar vídeos mais vistos: {e}. Usando dados simulados.")
            return self._mock_most_viewed_videos()

    def fetch_historical_catalog(self, limit: int = 440) -> List[Dict[str, Any]]:
        """
        Varre o acervo completo do 1º ao 440º vídeo do canal (Fila 3).

        :param limit: Limite total de vídeos a recuperar.
        :return: Lista com todo o acervo histórico.
        """
        if not self.youtube:
            return self._mock_historical_catalog(limit)

        try:
            videos = []
            next_page_token = None

            while len(videos) < limit:
                search_response = self.youtube.search().list(
                    channelId=YOUTUBE_CHANNEL_ID,
                    part="id,snippet",
                    order="date",
                    maxResults=min(50, limit - len(videos)),
                    pageToken=next_page_token,
                    type="video"
                ).execute()

                for item in search_response.get("items", []):
                    vid_id = item["id"]["videoId"]
                    snippet = item["snippet"]
                    videos.append({
                        "video_id": vid_id,
                        "title": snippet["title"],
                        "published_at": snippet["publishedAt"],
                        "url": f"https://www.youtube.com/watch?v={vid_id}",
                        "view_count": 0
                    })

                next_page_token = search_response.get("nextPageToken")
                if not next_page_token:
                    break

            logger.info(f"Fila 3 (Acervo Histórico): {len(videos)} vídeos catalogados.")
            return videos

        except Exception as e:
            logger.error(f"Erro ao varrer acervo histórico: {e}. Usando dados simulados.")
            return self._mock_historical_catalog(limit)

    def fetch_video_comments(self, video_id: str, max_comments: int = 100) -> List[Dict[str, Any]]:
        """
        Extrai comentários de um vídeo para análise de sentimento e mineração.

        :param video_id: ID do vídeo no YouTube.
        :param max_comments: Limite de comentários a extrair.
        :return: Lista de comentários contendo texto, autor e likes.
        """
        if not self.youtube:
            return self._mock_comments(video_id)

        try:
            response = self.youtube.commentThreads().list(
                videoId=video_id,
                part="snippet",
                maxResults=max_comments,
                textFormat="plainText"
            ).execute()

            comments = []
            for item in response.get("items", []):
                snippet = item["snippet"]["topLevelComment"]["snippet"]
                comments.append({
                    "author": snippet["authorDisplayName"],
                    "text": snippet["textDisplay"],
                    "like_count": snippet["likeCount"],
                    "published_at": snippet["publishedAt"]
                })

            return comments

        except Exception as e:
            logger.warning(f"Não foi possível buscar comentários para o vídeo {video_id}: {e}")
            return self._mock_comments(video_id)

    def _get_video_view_count(self, video_id: str) -> int:
        """Helper para consultar viewCount do vídeo."""
        try:
            resp = self.youtube.videos().list(part="statistics", id=video_id).execute()
            items = resp.get("items", [])
            if items:
                return int(items[0]["statistics"].get("viewCount", 0))
        except Exception:
            pass
        return 0

    # --- MOCK DATA FOR DEMO / LOCAL EXECUTION ---

    def _mock_recent_videos(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "video_id": "rec_001",
                "title": "Culto de Domingo - A Graça Abundante | IBPM CR",
                "published_at": (now - timedelta(hours=12)).isoformat(),
                "url": "https://www.youtube.com/watch?v=rec_001",
                "view_count": 1450
            },
            {
                "video_id": "rec_002",
                "title": "Quarta Profética - O Poder da Oração | IBPM CR",
                "published_at": (now - timedelta(hours=36)).isoformat(),
                "url": "https://www.youtube.com/watch?v=rec_002",
                "view_count": 980
            }
        ]

    def _mock_most_viewed_videos(self) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        return [
            {
                "video_id": "pop_001",
                "title": "Vencendo as Tempestades da Vida - Bispo Elcimar Lopes",
                "published_at": (now - timedelta(days=120)).isoformat(),
                "url": "https://www.youtube.com/watch?v=pop_001",
                "view_count": 18500
            },
            {
                "video_id": "pop_002",
                "title": "Voz de Libertação e Restauração Familiar | IBPM CR",
                "published_at": (now - timedelta(days=200)).isoformat(),
                "url": "https://www.youtube.com/watch?v=pop_002",
                "view_count": 12400
            }
        ]

    def _mock_historical_catalog(self, limit: int = 440) -> List[Dict[str, Any]]:
        now = datetime.now(timezone.utc)
        catalog = []
        for i in range(1, min(limit + 1, 15)):  # Gera 15 vídeos de exemplo
            catalog.append({
                "video_id": f"hist_{i:03d}",
                "title": f"Culto do Acervo IBPM CR #{i} - Mensagem e Louvor",
                "published_at": (now - timedelta(days=3 * i)).isoformat(),
                "url": f"https://www.youtube.com/watch?v=hist_{i:03d}",
                "view_count": 400 + i * 15
            })
        return catalog

    def _mock_comments(self, video_id: str) -> List[Dict[str, Any]]:
        return [
            {"author": "Irmã Maria", "text": "Gloria a Deus! Essa mensagem restaurou meu coração hoje.", "like_count": 12, "published_at": "2026-08-01T10:00:00Z"},
            {"author": "Obreiro Carlos", "text": "Peço oração pela minha família e saúde do meu pai.", "like_count": 5, "published_at": "2026-08-01T11:20:00Z"},
            {"author": "Jovem Lucas", "text": "Bispo Elcimar pregou com muita autoridade! Deus abençoe a IBPM CR.", "like_count": 8, "published_at": "2026-08-01T12:00:00Z"}
        ]


if __name__ == "__main__":
    client = YouTubeAPIClient()
    recents = client.fetch_recent_videos()
    print(f"Vídeos recentes encontrados: {len(recents)}")
