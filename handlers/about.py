from telegram import Update
from telegram.ext import ContextTypes

async def about_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("ℹ️ @AppBookinBot v1.0.0")
