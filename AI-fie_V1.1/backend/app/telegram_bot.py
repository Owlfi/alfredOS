import os
import asyncio
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

    try:
        await update.message.reply_text(
            "AI-fie Telegram is connected. Send me a message and I will route it through the system.",
            read_timeout=30,
            write_timeout=30,
            connect_timeout=20,
            pool_timeout=30,
        )
    except Exception as error:
        debug_log(f"[TELEGRAM] Error while sending /start reply: {error}")


async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or update.message.text is None:
        return

    user_message = update.message.text.strip()

    debug_log("[TELEGRAM] ===== New Telegram message received =====")
    debug_log(f"[TELEGRAM] Message: {user_message}")

    reply = "Something went wrong while processing your message."

    try:
        # Run blocking orchestrator off the async event loop
        reply = await asyncio.to_thread(
            handle_chat_message,
            source="telegram",
            message=user_message
        )

        debug_log(f"[TELEGRAM] Reply generated: {reply}")

    except Exception as error:
        debug_log(f"[TELEGRAM] Error while handling message: {error}")

    try:
        await update.message.reply_text(
            str(reply),
            read_timeout=30,
            write_timeout=30,
            connect_timeout=20,
            pool_timeout=30,
        )
        debug_log("[TELEGRAM] Reply sent successfully")

    except Exception as error:
        debug_log(f"[TELEGRAM] Error while sending reply to Telegram: {error}")


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    debug_log(f"[TELEGRAM] Unhandled bot error: {context.error}")


def main() -> None:
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in environment variables.")

    debug_log("[TELEGRAM] Starting Telegram bot...")

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message)
    )
    application.add_error_handler(error_handler)

    debug_log("[TELEGRAM] Bot is now polling for messages...")
    application.run_polling()


if __name__ == "__main__":
    main()