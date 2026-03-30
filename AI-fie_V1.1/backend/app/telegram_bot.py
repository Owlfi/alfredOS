import os
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters
from dotenv import load_dotenv

from app.services.chat_orchestrator import handle_chat_message
from app.utils.logger import debug_log

load_dotenv()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None:
        return

    await update.message.reply_text(
        "AI-fie Telegram is connected. Send me a message and I will route it through the system."
    )


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return

    user_message = update.message.text.strip()

    debug_log("[TELEGRAM] ===== New Telegram message received =====")
    debug_log(f"[TELEGRAM] Message: {user_message}")

    try:
        reply = handle_chat_message(
            source="telegram",
            message=user_message
        )
    except Exception as error:
        debug_log(f"[TELEGRAM] Error while handling message: {error}")
        reply = "Something went wrong while processing your message."

    await update.message.reply_text(reply)


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")

    debug_log("[TELEGRAM] Starting Telegram bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))

    debug_log("[TELEGRAM] Bot is now polling for messages...")
    application.run_polling()


if __name__ == "__main__":
    main()