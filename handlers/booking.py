from telegram.ext import ConversationHandler

# Empty placeholder ConversationHandler to allow app.py to start
booking_conversation_handler = ConversationHandler(
    entry_points=[],
    states={},
    fallbacks=[],
)
