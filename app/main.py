import os
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    InlineQueryHandler,
)
from uuid import uuid4

from parse_faculties import get_faculties
from parse_groups import get_groups
from parse_group_schedule import get_group_schedule, DAYS, pretty_day

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

UNI_SITE = "https://www.sgu.ru"


async def inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title=day,
            input_message_content=InputTextMessageContent(
                pretty_day(
                    get_group_schedule("http://www.sgu.ru/schedule/knt/do/341")[day]
                )
            ),
        )
        for day in DAYS
    ]
    await context.bot.answer_inline_query(update.inline_query.id, results)


if __name__ == "__main__":
    tok = os.getenv("TGBOT_TOKEN")
    if tok is None:
        print(
            "You must provide telegram token for the bot! Use env variable TGBOT_TOKEN"
        )
        exit(1)

    application = ApplicationBuilder().token(tok).build()

    inline_handler = InlineQueryHandler(inline)
    application.add_handler(inline_handler)

    application.run_polling()
