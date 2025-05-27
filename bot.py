import os
import logging
import requests
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    filters,
    ConversationHandler,
    ContextTypes,
)

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load environment variables
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
API_KEY = os.getenv("API_KEY")
API_URL = os.getenv("API_URL")

# States for conversation
BATCH, TEST_TYPE, TEST_NAME, FILE = range(4)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("🚫 Unauthorized user.")
        return ConversationHandler.END

    await update.message.reply_text(
        "👋 Hello admin! Let's upload a test PDF.\n\n"
        "Please send the batch (e.g. rm, tym, oym):"
    )
    return BATCH


async def batch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    batch = update.message.text.lower().strip()
    # Optional: validate batch
    if batch not in ("rm", "tym", "oym"):
        await update.message.reply_text(
            "❌ Invalid batch. Please send one of: rm, tym, oym"
        )
        return BATCH

    context.user_data["batch"] = batch
    await update.message.reply_text(
        "✅ Batch noted.\nNow send the test type (e.g. FTS, AIATS, PT, TE, NRT):"
    )
    return TEST_TYPE


async def test_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_type = update.message.text.upper().strip()
    # Optional: validate test_type
    valid_types = ("FTS", "AIATS", "PT", "TE", "NRT")
    if test_type not in valid_types:
        await update.message.reply_text(
            f"❌ Invalid test type. Please send one of: {', '.join(valid_types)}"
        )
        return TEST_TYPE

    context.user_data["test_type"] = test_type
    await update.message.reply_text(
        "✅ Test type noted.\nSend the test name (e.g. Test 1, AIATS March):"
    )
    return TEST_NAME


async def test_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    test_name = update.message.text.strip()
    if not test_name:
        await update.message.reply_text("❌ Test name cannot be empty. Please send again:")
        return TEST_NAME

    context.user_data["test_name"] = test_name
    await update.message.reply_text(
        "✅ Test name noted.\nNow send the PDF file:"
    )
    return FILE


async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message.document or not update.message.document.file_name.lower().endswith(".pdf"):
        await update.message.reply_text("❌ Please send a valid PDF file.")
        return FILE

    file = await update.message.document.get_file()
    file_path = await file.download_to_drive()

    # Prepare upload data
    with open(file_path, "rb") as f:
        files = {"file": (update.message.document.file_name, f, "application/pdf")}
        data = {
            "batch": context.user_data["batch"],
            "test_type": context.user_data["test_type"],
            "test_name": context.user_data["test_name"],
        }
        headers = {"X-API-KEY": API_KEY}

        try:
            resp = requests.post(API_URL, data=data, files=files, headers=headers)
        except Exception as e:
            await update.message.reply_text(f"❌ Upload failed due to network error:\n{e}")
            return ConversationHandler.END

    if resp.status_code == 200:
        await update.message.reply_text("✅ Upload successful! 🎉")
    else:
        try:
            error_msg = resp.json().get("error", "Unknown error")
        except Exception:
            error_msg = resp.text
        await update.message.reply_text(f"❌ Upload failed: {error_msg}")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ Upload cancelled.")
    return ConversationHandler.END


def main():
    if not all([BOT_TOKEN, ADMIN_ID, API_KEY, API_URL]):
        logger.error("Please set BOT_TOKEN, ADMIN_ID, API_KEY, and API_URL environment variables.")
        return

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            BATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_handler)],
            TEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_type_handler)],
            TEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_name_handler)],
            FILE: [MessageHandler(filters.Document.PDF, file_handler)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(conv_handler)

    logger.info("Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()
