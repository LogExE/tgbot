import os
import logging
from telegram import Update
from telegram.ext import filters, ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler

from uniparse import get_subjects, pretty_subjects

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)


async def get(update: Update, context: ContextTypes.DEFAULT_TYPE):
    data = pretty_subjects(get_subjects("https://www.sgu.ru/schedule/knt/do/341"))
    for line in data.split('\n'):
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text=line,
        )

async def what(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(chat_id=update.effective_chat.id, text="не понял")

if __name__ == "__main__":
    tok = os.getenv("TGBOT_TOKEN")
    if tok is None:
        print(
            "You must provide telegram token for the bot! Use env variable TGBOT_TOKEN"
        )
        exit()

    application = ApplicationBuilder().token(tok).build()

    start_handler = CommandHandler("get", get)
    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), what)
    application.add_handler(start_handler)
    application.add_handler(msg_handler)

    application.run_polling()
