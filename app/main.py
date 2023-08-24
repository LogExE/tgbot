import os
import logging
from telegram import ReplyKeyboardMarkup, ReplyKeyboardRemove, Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from uuid import uuid4

from parse_faculties import get_faculties
from parse_groups import get_groups
from parse_group_schedule import get_group_schedule, DAYS, pretty_day

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

UNI_SITE = "https://www.sgu.ru"

faculs = get_faculties()

GROUP, DAY, SHOW = range(3)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Этот бот умеет выводить расписание с сайта СГУ. Пожалуйста, выбери факультет.\nДля отмены используй /cancel",
        reply_markup=ReplyKeyboardMarkup(
            [list(faculs.keys())],
            one_time_keyboard=True,
            input_field_placeholder="<факультет>",
        ),
    )
    return GROUP


async def group(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["fac_link"] = faculs[update.message.text]
    context.chat_data["groups"] = get_groups(UNI_SITE + context.chat_data["fac_link"])
    await update.message.reply_text(
        (
            f"Выбранный факультет: {update.message.text}, адрес {context.chat_data['fac']}\n"
            "Прошу выбрать группу."
        ),
        reply_markup=ReplyKeyboardMarkup(
            [list(context.chat_data["groups"].keys())],
            one_time_keyboard=True,
            input_field_placeholder="<группа>",
        ),
    )
    return DAY


async def day(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["group_link"] = context.chat_data["groups"][update.message.text]
    await update.message.reply_text(
        f"Выбранная группа: {update.message.text}\nВыберите день.",
        reply_markup=ReplyKeyboardMarkup(
            [DAYS],
            one_time_keyboard=True,
            input_field_placeholder="<группа>",
        ),
    )
    return SHOW


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Спасибо за обращение. Расписание:")
    await update.message.reply_text(
        get_group_schedule(UNI_SITE + context.chat_data["group_link"])[
            update.message.text
        ]
    )
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "До встречи!", reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END


if __name__ == "__main__":
    tok = os.getenv("TGBOT_TOKEN")
    if tok is None:
        print(
            "You must provide telegram token for the bot! Use env variable TGBOT_TOKEN"
        )
        exit(1)

    application = ApplicationBuilder().token(tok).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            GROUP: [MessageHandler(filters.TEXT & (~filters.COMMAND), group)],
            DAY: [MessageHandler(filters.TEXT & (~filters.COMMAND), day)],
            SHOW: [MessageHandler(filters.TEXT & (~filters.COMMAND), show)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    application.run_polling()
