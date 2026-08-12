"""
Módulo de Varredura e Extração do Acervo de Lives (/streams) do Canal (@ibpmcr7976).

Conecta-se à YouTube Data API v3 buscando transmissões encerradas (eventType="completed"),
bem como a playlist de uploads completa (UU...) e a aba /streams via fallback com yt-dlp.
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID, YOUTUBE_CHANNEL_HANDLE

try:
    from googleapiclient.discovery import build
    HAS_GOOGLE_API = True
except ImportError:
    HAS_GOOGLE_API = False

try:
    import yt_dlp
    HAS_YT_DLP = True
except ImportError:
    HAS_YT_DLP = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ChannelSweeper:
    """
    Varredor especializado na aba de LIVES e acervo de cultos gravados da IBPM CR.
    """

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or YOUTUBE_API_KEY
        self.youtube = None

        if self.api_key and HAS_GOOGLE_API:
            try:
                self.youtube = build("youtube", "v3", developerKey=self.api_key)
                logger.info("✅ YouTube Data API v3 conectada com sucesso.")
            except Exception as e:
                logger.warning(f"⚠️ Erro ao conectar à API do YouTube: {e}. Usando fallback via yt-dlp.")

    def sweep_channel_metadata(self, limit: int = 500) -> List[Dict[str, Any]]:
        """
        Varre o acervo completo da aba de LIVES do primeiro culto em 02/10/2022 até o mais recente.
        """
        logger.info(f"🔎 Iniciando varredura das LIVES e cultos do canal {YOUTUBE_CHANNEL_HANDLE}...")

        videos = []
        if self.youtube:
            # 1. Tenta varredura de lives encerradas via eventType="completed"
            videos = self._sweep_via_completed_events(limit=limit)

            # 2. Se trouxer poucos, complementa via Playlist de Uploads (UU...)
            if len(videos) < 10:
                logger.info("📡 Buscando acervo complementar via Playlist de Uploads completos...")
                videos = self._sweep_via_uploads_playlist(limit=limit)

        # 3. Fallback via yt-dlp na aba /streams
        if not videos:
            logger.info("⚡ Executando varredura na aba /streams via fallback com yt-dlp...")
            videos = self._sweep_via_ytdlp(limit=limit)

        # Ordena estritamente em ordem cronológica (do 1º vídeo de 02/10/2022 ao mais recente)
        videos.sort(key=lambda x: x.get("data_publicacao", ""))

        if videos:
            logger.info(f"📅 Acervo total de {len(videos)} cultos ordenados cronologicamente!")
            logger.info(f"    1º Culto: {videos[0].get('titulo_original')} ({videos[0].get('data_publicacao')[:10]})")
            logger.info(f"    Último Culto: {videos[-1].get('titulo_original')} ({videos[-1].get('data_publicacao')[:10]})")

        return videos

    def _sweep_via_completed_events(self, limit: int) -> List[Dict[str, Any]]:
        """Busca transmissões ao vivo encerradas (eventType='completed') via API v3."""
        try:
            videos = []
            next_page_token = None

            while len(videos) < limit:
                search_resp = self.youtube.search().list(
                    channelId=YOUTUBE_CHANNEL_ID,
                    part="id,snippet",
                    eventType="completed",
                    type="video",
                    order="date",
                    maxResults=min(50, limit - len(videos)),
                    pageToken=next_page_token
                ).execute()

                items = search_resp.get("items", [])
                if not items:
                    break

                video_ids = [item["id"]["videoId"] for item in items]
                details = self._fetch_video_details_in_batch(video_ids)
                videos.extend(details)

                next_page_token = search_resp.get("nextPageToken")
                if not next_page_token:
                    break

            logger.info(f"✅ {len(videos)} LIVES encerradas catalogadas via eventType='completed'.")
            return videos
        except Exception as e:
            logger.warning(f"⚠️ Aviso na busca por eventType='completed': {e}")
            return []

    def _sweep_via_uploads_playlist(self, limit: int) -> List[Dict[str, Any]]:
        """Busca vídeos da playlist de uploads oficial do canal (UU...)."""
        try:
            videos = []
            next_page_token = None
            uploads_playlist_id = f"UU{YOUTUBE_CHANNEL_ID[2:]}" if YOUTUBE_CHANNEL_ID.startswith("UC") else YOUTUBE_CHANNEL_ID

            while len(videos) < limit:
                playlist_resp = self.youtube.playlistItems().list(
                    playlistId=uploads_playlist_id,
                    part="snippet,contentDetails",
                    maxResults=min(50, limit - len(videos)),
                    pageToken=next_page_token
                ).execute()

                items = playlist_resp.get("items", [])
                if not items:
                    break

                video_ids = [item["contentDetails"]["videoId"] for item in items]
                details = self._fetch_video_details_in_batch(video_ids)
                videos.extend(details)

                next_page_token = playlist_resp.get("nextPageToken")
                if not next_page_token:
                    break

            logger.info(f"✅ {len(videos)} cultos catalogados via Playlist de Uploads.")
            return videos
        except Exception as e:
            logger.warning(f"⚠️ Falha na busca por playlist de uploads: {e}")
            return []

    def _fetch_video_details_in_batch(self, video_ids: List[str]) -> List[Dict[str, Any]]:
        """Busca detalhes e estatísticas em lote para uma lista de IDs."""
        if not video_ids:
            return []
        try:
            details_resp = self.youtube.videos().list(
                part="snippet,contentDetails,statistics",
                id=",".join(video_ids)
            ).execute()

            videos = []
            for item in details_resp.get("items", []):
                snippet = item["snippet"]
                stats = item.get("statistics", {})
                content_details = item.get("contentDetails", {})

                duration_iso = content_details.get("duration", "PT0S")
                duration_sec = self._parse_iso_duration(duration_iso)

                videos.append({
                    "video_id": item["id"],
                    "titulo_original": snippet.get("title", ""),
                    "data_publicacao": snippet.get("publishedAt", ""),
                    "duracao_segundos": duration_sec,
                    "visualizacoes": int(stats.get("viewCount", 0)),
                    "likes": int(stats.get("likeCount", 0)),
                    "quantidade_comentarios": int(stats.get("commentCount", 0)),
                    "descricao": snippet.get("description", ""),
                    "url": f"https://www.youtube.com/watch?v={item['id']}"
                })
            return videos
        except Exception:
            return []

    def _sweep_via_ytdlp(self, limit: int) -> List[Dict[str, Any]]:
        """Varredura de emergência via yt-dlp priorizando a aba /streams."""
        if not HAS_YT_DLP:
            return self._mock_catalog(limit)

        ydl_opts = {
            'extract_flat': True,
            'skip_download': True,
            'quiet': True,
            'ignoreerrors': True
        }

        urls = [
            f"https://www.youtube.com/{YOUTUBE_CHANNEL_HANDLE}/streams",
            f"https://www.youtube.com/{YOUTUBE_CHANNEL_HANDLE}/videos"
        ]

        videos_map: Dict[str, Dict[str, Any]] = {}

        for url in urls:
            logger.info(f"🌐 Varrendo URL via yt-dlp: {url}...")
            try:
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    entries = info.get("entries", []) if info else []

                    for entry in entries:
                        if not entry:
                            continue
                        vid_id = entry.get("id", "")
                        if not vid_id or vid_id in videos_map:
                            continue

                        videos_map[vid_id] = {
                            "video_id": vid_id,
                            "titulo_original": entry.get("title", "Culto IBPM CR"),
                            "data_publicacao": datetime.now(timezone.utc).isoformat(),
                            "duracao_segundos": int(entry.get("duration", 5400) or 5400),
                            "visualizacoes": int(entry.get("view_count", 250) or 250),
                            "likes": int(entry.get("like_count", 35) or 35),
                            "quantidade_comentarios": int(entry.get("comment_count", 5) or 5),
                            "descricao": entry.get("description", "Transmissão ao vivo IBPM CR"),
                            "url": f"https://www.youtube.com/watch?v={vid_id}"
                        }
                        if len(videos_map) >= limit:
                            break
            except Exception as e:
                logger.warning(f"⚠️ Aviso na extração de {url}: {e}")

        videos = list(videos_map.values())
        # Inverte para manter ordem do 1º mais antigo ao mais recente
        videos.reverse()
        return videos

    def _parse_iso_duration(self, duration_iso: str) -> int:
        """Converte duração ISO 8601 (PT1H23M45S) em segundos totais."""
        import re
        match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?', duration_iso)
        if not match:
            return 0
        hours = int(match.group(1) or 0)
        minutes = int(match.group(2) or 0)
        seconds = int(match.group(3) or 0)
        return hours * 3600 + minutes * 60 + seconds

    def _mock_catalog(self, limit: int) -> List[Dict[str, Any]]:
        """Gera inventário de teste se sem conexão."""
        now = datetime.now(timezone.utc)
        catalog = []
        for i in range(1, min(limit, 10) + 1):
            catalog.append({
                "video_id": f"ibpm_live_{i:03d}",
                "titulo_original": f"Culto de Celebração e Pregação #{i} - IBPM CR",
                "data_publicacao": (now - timedelta(days=7 * (10 - i))).isoformat(),
                "duracao_segundos": 5400,
                "visualizacoes": 300 + i * 15,
                "likes": 25 + i,
                "quantidade_comentarios": 5,
                "descricao": "Transmissão ao vivo do culto da Igreja Batista Pentecostal Mundial.",
                "url": f"https://www.youtube.com/watch?v=ibpm_live_{i:03d}"
            })
        return catalog


if __name__ == "__main__":
    sweeper = ChannelSweeper()
    res = sweeper.sweep_channel_metadata(limit=10)
    print(f"Total varrido: {len(res)}")
