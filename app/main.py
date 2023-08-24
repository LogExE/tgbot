import os
import logging
from telegram import Update, InlineQueryResultArticle, InputTextMessageContent
from telegram.ext import (
    ApplicationBuilder,
    ContextTypes,
    InlineQueryHandler,
)
from uuid import uuid4

from uniparse import get_subjects, Subject, DAYS

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

times = [
    "8:20-9:50",
    "10:00-11:30",
    "12:05-13:40",
    "13:50-15:25",
    "15:35-17:10",
    "17:20-18:40",
    "18:45-20:05",
    "20:10-21:30",
]


def pretty_day(day: list[list[Subject]]) -> str:
    lines = []
    for time, subj in zip(times, day):
        lines.append(f"{time}:")
        for sub in subj:
            lines.append(str(sub))
    return "\n".join(lines)


async def inline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.inline_query.query
    if not query:
        return
    results = [
        InlineQueryResultArticle(
            id=uuid4(),
            title=day,
            input_message_content=InputTextMessageContent(
                pretty_day(get_subjects("https://www.sgu.ru/schedule/knt/do/341")[day])
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
