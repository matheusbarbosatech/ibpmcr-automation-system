"""
Cliente de Publicação Assíncrona via Instagram Graph API (Reels) - IBPM CR Automation System.

Implementa a máquina de estados para publicação de Reels (9:16) no Instagram:
1. Criação do Contêiner de Mídia (POST /media com video_url público)
2. Sondagem de Status (Polling GET /{container_id} aguardando status FINISHED)
3. Publicação do Contêiner (POST /media_publish com creation_id)
"""

import time
import requests
from typing import Dict, Any, Optional

from src.core.config import settings
from src.core.logger import get_logger

logger = get_logger("InstagramGraphAPIClient")


class InstagramGraphAPIClient:
    """
    Cliente oficial para integração com a Instagram Graph API (Meta).
    """

    def __init__(self, access_token: Optional[str] = None, account_id: Optional[str] = None):
        self.access_token = access_token or settings.INSTAGRAM_ACCESS_TOKEN
        self.account_id = account_id or settings.INSTAGRAM_ACCOUNT_ID
        self.api_version = "v22.0"
        self.base_url = f"https://graph.facebook.com/{self.api_version}"

    def create_container(self, video_url: str, caption: str, job_id: str = "job_ig_container") -> str:
        """
        Passo 1: Submete o pedido de criação do Contêiner de Mídia para o Reel.
        O video_url deve ser acessível publicamente na internet (S3, Cloudflare R2, Rclone CDN).
        """
        if not self.access_token or not self.account_id:
            logger.warning("Credenciais do Instagram não configuradas. Retornando container_id simulado.", job_id=job_id)
            return f"SIMULATED_CONTAINER_{int(time.time())}"

        url = f"{self.base_url}/{self.account_id}/media"
        payload = {
            "media_type": "REELS",
            "video_url": video_url,
            "caption": caption[:2200],
            "share_to_feed": "true",
            "access_token": self.access_token
        }

        logger.info("Criando contêiner de mídia no Instagram Graph API", job_id=job_id, video_url=video_url)
        res = requests.post(url, data=payload, timeout=30)
        data = res.json()

        if res.status_code != 200 or "id" not in data:
            logger.error("Falha ao criar contêiner no Instagram", job_id=job_id, error=data)
            raise RuntimeError(f"Erro no Meta Graph API: {data}")

        container_id = data["id"]
        logger.info("Contêiner de mídia criado com sucesso", job_id=job_id, container_id=container_id)
        return container_id

    def check_container_status(self, container_id: str, job_id: str = "job_ig_status") -> Dict[str, Any]:
        """
        Passo 2: Verifica o status de transcodificação e processamento do contêiner.
        Retorna status_code: 'IN_PROGRESS', 'FINISHED', 'ERROR' ou 'EXPIRED'.
        """
        if container_id.startswith("SIMULATED_"):
            return {"status_code": "FINISHED", "status": "SIMULATED_SUCCESS"}

        url = f"{self.base_url}/{container_id}"
        params = {
            "fields": "status_code,status",
            "access_token": self.access_token
        }

        res = requests.get(url, params=params, timeout=30)
        data = res.json()

        if res.status_code != 200:
            logger.error("Falha ao checar status do contêiner", job_id=job_id, container_id=container_id, error=data)
            raise RuntimeError(f"Erro na checagem de status: {data}")

        status_code = data.get("status_code", "UNKNOWN")
        logger.info("Status do contêiner do Instagram", job_id=job_id, container_id=container_id, status_code=status_code)
        return data

    def publish_container(self, container_id: str, job_id: str = "job_ig_publish") -> str:
        """
        Passo 3: Publica o contêiner transcodificado e aprovado no feed/reels do Instagram.
        """
        if container_id.startswith("SIMULATED_"):
            return f"SIMULATED_MEDIA_ID_{int(time.time())}"

        url = f"{self.base_url}/{self.account_id}/media_publish"
        payload = {
            "creation_id": container_id,
            "access_token": self.access_token
        }

        logger.info("Publicando contêiner aprovado no Instagram", job_id=job_id, container_id=container_id)
        res = requests.post(url, data=payload, timeout=30)
        data = res.json()

        if res.status_code != 200 or "id" not in data:
            logger.error("Falha ao publicar contêiner no Instagram", job_id=job_id, container_id=container_id, error=data)
            raise RuntimeError(f"Erro na publicação do Instagram: {data}")

        media_id = data["id"]
        logger.info("Reel publicado com sucesso no Instagram!", job_id=job_id, media_id=media_id)
        return media_id

    def publish_reel_async_pipeline(
        self,
        video_url: str,
        caption: str,
        poll_interval_sec: int = 10,
        timeout_sec: int = 300,
        job_id: str = "job_ig_pipeline"
    ) -> Dict[str, Any]:
        """
        Orquestra o ciclo completo (Criação ➔ Polling ➔ Publicação) de um Reel no Instagram.
        """
        container_id = self.create_container(video_url, caption, job_id=job_id)
        start_time = time.time()

        while (time.time() - start_time) < timeout_sec:
            status_data = self.check_container_status(container_id, job_id=job_id)
            status_code = status_data.get("status_code", "")

            if status_code == "FINISHED":
                media_id = self.publish_container(container_id, job_id=job_id)
                return {
                    "status": "published",
                    "media_id": media_id,
                    "container_id": container_id,
                    "instagram_url": f"https://www.instagram.com/p/{media_id}"
                }
            elif status_code in ["ERROR", "EXPIRED"]:
                raise RuntimeError(f"Falha no processamento do Reel pela Meta: {status_data}")

            time.sleep(poll_interval_sec)

        raise TimeoutError(f"Tempo limite ({timeout_sec}s) excedido aguardando transcodificação do Reel no Instagram.")
