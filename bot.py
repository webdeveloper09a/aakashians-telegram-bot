import logging
import requests
from telegram import Update, InputFile
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

API_URL = "https://aakashianssneet.up.railway.app/upload"  # Your upload API endpoint
API_KEY = "leakerswebsitehere"  # Your upload API key
ADMIN_ID = 7796598050  # Your Telegram user ID to restrict access

BATCH, TEST_TYPE, TEST_NAME, FILE = range(4)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Unauthorized")
        return ConversationHandler.END
    await update.message.reply_text("Send batch (e.g. rm, tym, oym):")
    return BATCH

async def batch_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['batch'] = update.message.text.lower()
    await update.message.reply_text("Send test type (e.g. FTS, AIATS, PT, TE, NRT):")
    return TEST_TYPE

async def test_type_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['test_type'] = update.message.text.upper()
    await update.message.reply_text("Send test name (e.g. Test 1, AIATS March):")
    return TEST_NAME

async def test_name_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['test_name'] = update.message.text
    await update.message.reply_text("Send the PDF file now:")
    return FILE

async def file_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.document is None or not update.message.document.file_name.endswith('.pdf'):
        await update.message.reply_text("Please send a PDF document.")
        return FILE

    file = await update.message.document.get_file()
    file_path = await file.download_to_drive()

    # Upload file to your API
    with open(file_path, 'rb') as f:
        files = {'file': (update.message.document.file_name, f, 'application/pdf')}
        data = {
            'batch': context.user_data['batch'],
            'test_type': context.user_data['test_type'],
            'test_name': context.user_data['test_name']
        }
        headers = {'X-API-KEY': API_KEY}

        response = requests.post(API_URL, data=data, files=files, headers=headers)

    if response.status_code == 200:
        await update.message.reply_text("Upload successful!")
    else:
        await update.message.reply_text(f"Upload failed: {response.json().get('error', 'Unknown error')}")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Upload cancelled.")
    return ConversationHandler.END

def main():
    app = ApplicationBuilder().token("7708512334:AAHltdbTA632hHy2E1gQ5F4H4o-MDVGboH4").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            BATCH: [MessageHandler(filters.TEXT & ~filters.COMMAND, batch_handler)],
            TEST_TYPE: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_type_handler)],
            TEST_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, test_name_handler)],
            FILE: [MessageHandler(filters.Document.PDF, file_handler)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )

    app.add_handler(conv_handler)
    app.run_polling()

if __name__ == '__main__':
    main()
