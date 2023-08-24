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

START, FAC_SELECT, GROUP_SELECT, DAY_SELECT, DONE = range(5)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Этот бот умеет получать и выводить расписание СГУ. Просьба: не используйте его слишком часто, иначе ему прилетит блокировка с сайта СГУ.",
        reply_markup=ReplyKeyboardMarkup(
            [["Хорошо."]],
            one_time_keyboard=True,
        ),
    )
    return START


async def fac_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Пожалуйста, выбери факультет.",
        reply_markup=ReplyKeyboardMarkup(
            [[fac] for fac in faculs.keys()],
            one_time_keyboard=True,
            input_field_placeholder="<факультет>",
        ),
    )
    return FAC_SELECT


async def group_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["fac_link"] = faculs[update.message.text]
    logging.log(logging.INFO, "Fac link  %s", context.chat_data["fac_link"])
    context.chat_data["groups"] = get_groups(UNI_SITE + context.chat_data["fac_link"])
    await update.message.reply_text(
        (
            f"Выбранный факультет: {update.message.text}, адрес {context.chat_data['fac_link']}\n"
            "Прошу выбрать группу."
        ),
        reply_markup=ReplyKeyboardMarkup(
            [[group] for group in context.chat_data["groups"].keys()],
            one_time_keyboard=True,
            input_field_placeholder="<группа>",
        ),
    )
    return GROUP_SELECT


async def day_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["group_link"] = context.chat_data["groups"][update.message.text]
    logging.log(logging.INFO, "Group link  %s", context.chat_data["group_link"])
    await update.message.reply_text(
        f"Выбранная группа: {update.message.text}\nВыберите день.",
        reply_markup=ReplyKeyboardMarkup(
            [DAYS],
            one_time_keyboard=True,
            input_field_placeholder="<группа>",
        ),
    )
    return DAY_SELECT


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.log(logging.INFO, "Day  %s", update.message.text)
    await update.message.reply_text(
        f'Спасибо за обращение! Расписание на день "{update.message.text}":'
        + pretty_day(
            get_group_schedule(UNI_SITE + context.chat_data["group_link"])[
                update.message.text
            ]
        )
    )
    await update.message.reply_text(
        "Для нового запроса напиши /another. Для выхода пиши /quit\n"
        "Если расписание не отобразилось, то, скорее всего, бот еще не знает, как отображать расписание с вашего факультета."
    )
    return DONE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("До встречи!", reply_markup=ReplyKeyboardRemove())
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
            START: [MessageHandler(filters.Regex("^Хорошо.$"), fac_select)],
            FAC_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), group_select)
            ],
            GROUP_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), day_select)
            ],
            DAY_SELECT: [MessageHandler(filters.TEXT & (~filters.COMMAND), show)],
            DONE: [
                CommandHandler("another", fac_select),
                CommandHandler("quit", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    application.run_polling()
