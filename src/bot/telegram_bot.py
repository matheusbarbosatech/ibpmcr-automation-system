"""
Bot de Atendimento e Acolhimento Comunitário no Telegram (python-telegram-bot).

Proporciona menu interativo com botões InlineKeyboardMarkup para horários de cultos,
pedidos de oração sigilosos, download de e-books em PDF e confirmação de escalas de voluntários.
"""

from __future__ import annotations
import os
import logging
from typing import Optional
from pathlib import Path

import sys
sys.path.append(str(Path(__file__).resolve().parent.parent.parent))
from config.settings import TELEGRAM_BOT_TOKEN

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
    HAS_TELEGRAM_BOT = True
except ImportError:
    HAS_TELEGRAM_BOT = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class IBPMTelegramBot:
    """
    Bot interativo no Telegram para atendimento e engajamento da IBPM CR.
    """

    def __init__(self, token: Optional[str] = None):
        """
        Inicializa as credenciais do Bot.
        """
        self.token = token or TELEGRAM_BOT_TOKEN

    def build_main_menu(self) -> Optional[InlineKeyboardMarkup]:
        """
        Monta o menu principal interativo com InlineKeyboardMarkup.
        """
        if not HAS_TELEGRAM_BOT:
            return None

        keyboard = [
            [InlineKeyboardButton("📅 Horários & Endereço", callback_data="menu_horarios")],
            [InlineKeyboardButton("🙏 Pedido de Oração Sigiloso", callback_data="menu_oracao")],
            [InlineKeyboardButton("📚 Baixar Devocionais em PDF", callback_data="menu_pdf")],
            [InlineKeyboardButton("🙋‍♂️ Escala de Voluntários", callback_data="menu_escala")],
            [InlineKeyboardButton("🔴 Canal no YouTube @ibpmcr7976", url="https://www.youtube.com/@ibpmcr7976")]
        ]
        return InlineKeyboardMarkup(keyboard)

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Handler do comando /start.
        """
        welcome_text = (
            "<b>Graça e paz! Seja muito bem-vindo ao Bot Oficial da IBPM CR!</b>\n\n"
            "Como podemos abençoar a sua vida hoje? Escolha uma das opções abaixo no menu:"
        )
        if update.message:
            await update.message.reply_text(welcome_text, reply_markup=self.build_main_menu(), parse_mode="HTML")

    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Trata o clique dos botões do menu interativo.
        """
        query = update.callback_query
        await query.answer()

        data = query.data

        if data == "menu_horarios":
            text = (
                "📍 <b>Endereço da IBPM CR Sede:</b>\n"
                "Rua Ajurana, 510 - Campo Grande, Rio de Janeiro - RJ\n\n"
                "⏰ <b>Agenda Litúrgica Semanal:</b>\n"
                "• <b>Quarta Profética:</b> 19:30\n"
                "• <b>Domingo - EBD:</b> 09:00\n"
                "• <b>Domingo - Culto da Família:</b> 18:30"
            )
            await query.edit_message_text(text, reply_markup=self.build_main_menu(), parse_mode="HTML")

        elif data == "menu_oracao":
            text = (
                "🙏 <b>Pedido de Oração Sigiloso</b>\n\n"
                "Escreva o seu pedido nesta conversa. Ele será direcionado sigilosamente à nossa equipe pastoral de intercessão!"
            )
            await query.edit_message_text(text, parse_mode="HTML")

        elif data == "menu_pdf":
            text = (
                "📚 <b>Materiais e E-books em PDF:</b>\n\n"
                "Clique para baixar o Devocional Semanal da IBPM CR."
            )
            keyboard = [[InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu")]]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "menu_escala":
            text = (
                "🙋‍♂️ <b>Confirmação de Escala de Voluntários</b>\n\n"
                "Você foi escalado para servir no departamento de <b>Mídia</b> no próximo Domingo às 18:30."
            )
            keyboard = [
                [InlineKeyboardButton("✅ Confirmar Presença", callback_data="confirm_escala")],
                [InlineKeyboardButton("🔄 Solicitar Troca", callback_data="swap_escala")],
                [InlineKeyboardButton("🔙 Voltar ao Menu", callback_data="main_menu")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="HTML")

        elif data == "confirm_escala":
            await query.edit_message_text("✅ <b>Presença confirmada na escala! Deus abençoe seu servir.</b>", parse_mode="HTML")

        elif data == "swap_escala":
            await query.edit_message_text("🔄 <b>Solicitação de troca enviada ao líder de departamento.</b>", parse_mode="HTML")

        elif data == "main_menu":
            await query.edit_message_text("Como podemos abençoar sua vida hoje?", reply_markup=self.build_main_menu())

    def run(self) -> None:
        """
        Inicia a execução do Bot no Telegram.
        """
        if not HAS_TELEGRAM_BOT or not self.token:
            logger.warning("⚠️ Token do Telegram não configurado ou python-telegram-bot indisponível. Bot não iniciado.")
            return

        logger.info("🤖 Iniciando Bot do Telegram da IBPM CR...")
        app = ApplicationBuilder().token(self.token).build()
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.run_polling()


if __name__ == "__main__":
    bot = IBPMTelegramBot()
    print("Módulo Telegram Bot pronto. Para iniciar polling, configure o token no .env.")
