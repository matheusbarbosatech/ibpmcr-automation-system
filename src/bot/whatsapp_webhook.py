"""
Webhook FastAPI para Integração com Twilio WhatsApp API.

Recebe e responde automaticamente mensagens via WhatsApp para o atendimento comunitário da IBPM CR.
"""

import logging
from typing import Dict, Any
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_NUMBER

try:
    from fastapi import FastAPI, Form, Response
    from twilio.twiml.messaging_response import MessagingResponse
    from twilio.rest import Client as TwilioClient
    HAS_FASTAPI_TWILIO = True
except ImportError:
    HAS_FASTAPI_TWILIO = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="IBPM CR WhatsApp Webhook Service", version="1.0.0")


@app.get("/")
def health_check():
    """
    Endpoint de status da API.
    """
    return {"status": "online", "service": "IBPM CR WhatsApp Webhook"}


@app.post("/webhook/whatsapp")
async def whatsapp_webhook(From: str = Form(""), Body: str = Form("")):
    """
    Recebe mensagens enviadas ao número de WhatsApp da igreja via Twilio.

    :param From: Número de envio do WhatsApp do usuário.
    :param Body: Texto da mensagem recebida.
    :return: Resposta TWiML formatada em XML.
    """
    logger.info(f"📱 Mensagem de WhatsApp recebida de {From}: '{Body}'")

    if not HAS_FASTAPI_TWILIO:
        return {"message": "FastAPI ou Twilio não instalado."}

    resp = MessagingResponse()
    msg_text = Body.lower().strip()

    if "culto" in msg_text or "horario" in msg_text or "endereço" in msg_text:
        resp.message(
            "📍 *IBPM CR Sede Matriz*\n"
            "Rua Ajurana, 510 - Campo Grande, RJ\n\n"
            "⏰ *Horários de Culto:*\n"
            "• Quarta Profética: 19:30\n"
            "• Domingo: 09:00 (EBD) e 18:30 (Culto da Família)"
        )
    elif "oração" in msg_text or "oracao" in msg_text:
        resp.message(
            "🙏 Seu pedido de oração foi recebido e encaminhado ao nosso grupo de intercessão pastoral. "
            "Deus tem grandes coisas para a sua vida!"
        )
    else:
        resp.message(
            "Graça e Paz! Seja bem-vindo à *IBPM CR* (@ibpmcr7976).\n\n"
            "Digite uma das opções para atendimento:\n"
            "1. *Cultos* (Horários e Endereço)\n"
            "2. *Oração* (Enviar pedido de oração)\n"
            "3. *Devocional* (Receber devocional do dia)"
        )

    return Response(content=str(resp), media_type="application/xml")


def send_whatsapp_message(to_number: str, message_body: str, media_url: str = None) -> bool:
    """
    Função utilitária para enviar mensagem ativa via WhatsApp Twilio (ex: cartão de aniversário ou avisos).

    :param to_number: Número do destinatário (ex: 'whatsapp:+5521999999999').
    :param message_body: Texto da mensagem.
    :param media_url: URL opcional da imagem (cartão de aniversário).
    :return: Bool indicando sucesso.
    """
    if not HAS_FASTAPI_TWILIO or not TWILIO_ACCOUNT_SID or not TWILIO_AUTH_TOKEN:
        logger.warning("⚠️ Twilio não configurado. Simulação de envio ativada.")
        return True

    try:
        client = TwilioClient(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        kwargs = {
            "from_": TWILIO_WHATSAPP_NUMBER,
            "to": to_number,
            "body": message_body
        }
        if media_url:
            kwargs["media_url"] = [media_url]

        msg = client.messages.create(**kwargs)
        logger.info(f"✅ Mensagem enviada via WhatsApp para {to_number}. SID: {msg.sid}")
        return True
    except Exception as e:
        logger.error(f"❌ Erro ao enviar WhatsApp via Twilio: {e}")
        return False


if __name__ == "__main__":
    print("Módulo Webhook WhatsApp inicializado.")
