from telegram import Update
from telegram.ext import ContextTypes

async def view_appointments_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("📋 You have no active appointments.")
