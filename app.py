import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    CallbackQueryHandler,
)
from utils.config import settings
from utils.logger import setup_logging
from services.database import init_db
from services.scheduler import auto_complete_past_appointments

# Handler imports (placeholders mapped to actual module endpoints)
from handlers.start import start_command, main_menu_callback
from handlers.booking import booking_conversation_handler
from handlers.appointments import view_appointments_command
from handlers.reschedule import reschedule_conversation_handler
from handlers.cancel import cancel_conversation_handler
from handlers.admin import admin_command
from handlers.settings import settings_command
from handlers.help import help_command
from handlers.about import about_command

logger = logging.getLogger(__name__)

async def post_init(application: Application) -> None:
    """Runs database initializations and sets up recurring background tasks."""
    logger.info("Initializing database tables...")
    await init_db()

    # Schedule periodic task to complete past appointments every 15 minutes
    if application.job_queue:
        application.job_queue.run_repeating(
            auto_complete_past_appointments,
            interval=900,  # 15 minutes in seconds
            first=10,
            name="auto_complete_appointments"
        )
        logger.info("JobQueue tasks registered successfully.")

def main() -> None:
    """Sets up and starts the Telegram Bot."""
    setup_logging()
    
    if not settings.BOT_TOKEN:
        logger.critical("BOT_TOKEN is not set in environment variables! Exiting.")
        return

    logger.info("Starting @AppBookinBot...")

    # Build Application
    builder = Application.builder().token(settings.BOT_TOKEN).post_init(post_init)
    app = builder.build()

    # Conversation Handlers
    app.add_handler(booking_conversation_handler)
    app.add_handler(reschedule_conversation_handler)
    app.add_handler(cancel_conversation_handler)

    # Core Command Handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("appointments", view_appointments_command))
    app.add_handler(CommandHandler("settings", settings_command))
    app.add_handler(CommandHandler("admin", admin_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("about", about_command))

    # Menu Callbacks
    app.add_handler(CallbackQueryHandler(main_menu_callback, pattern="^menu_"))

    # Global Error Handler
    async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        logger.error("Exception while handling an update:", exc_info=context.error)
        if isinstance(update, Update) and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ An unexpected error occurred while processing your request. Please try again later."
            )

    app.add_error_handler(error_handler)

    # Start Polling
    logger.info("Bot is active and polling for updates...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
