import os
import logging
from typing import Optional, Tuple
from telegram import (
    Chat,
    ChatMember,
    ChatMemberUpdated,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    Update,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    ChatMemberHandler,
    filters,
)
from myshared import UniDownException

from parse_faculties import get_faculties
from parse_groups import get_groups
from parse_group_schedule import get_group_schedule, DAYS, pretty_day

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

UNI_SITE = "https://www.sgu.ru"

faculs = None


def get_faculs():
    global faculs
    if faculs is None:
        faculs = get_faculties()
    return faculs


START, FAC_SELECT, GROUP_SELECT, DAY_SELECT, DONE = range(5)


async def uni_down_msg(update: Update):
    await update.message.reply_text(
        "Сайт университета не отвечает. Возможно, бот сейчас находится во временной блокировке..."
    )


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
    try:
        await update.message.reply_text(
            "Пожалуйста, выбери факультет.",
            reply_markup=ReplyKeyboardMarkup(
                [[fac] for fac in get_faculs().keys()],
                one_time_keyboard=True,
                input_field_placeholder="<факультет>",
            ),
        )
        return FAC_SELECT
    except UniDownException:
        await uni_down_msg(update)


async def group_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.chat_data["fac_link"] = get_faculs()[update.message.text]
    except KeyError:
        await update.message.reply_text("Не знаю такого факультета. Попробуй еще раз")
        return
    logger.log(
        logging.INFO,
        "Fac %s, link  %s",
        update.message.text,
        context.chat_data["fac_link"],
    )
    try:
        context.chat_data["groups"] = get_groups(
            UNI_SITE + context.chat_data["fac_link"]
        )
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
    except UniDownException:
        await uni_down_msg(update)


async def day_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.chat_data["group_link"] = context.chat_data["groups"][
            update.message.text
        ]
    except KeyError:
        await update.message.reply_text(
            "Не знаю такой группы. Попробуй еще раз",
        )
        return
    logger.log(
        logging.INFO,
        "Group %s, link  %s",
        update.message.text,
        context.chat_data["group_link"],
    )
    await update.message.reply_text(
        f"Выбранная группа: {update.message.text}\nВыберите день.",
        reply_markup=ReplyKeyboardMarkup(
            [DAYS],
            one_time_keyboard=True,
            input_field_placeholder="<день>",
        ),
    )
    return DAY_SELECT


async def same(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        f"Выберите день.",
        reply_markup=ReplyKeyboardMarkup(
            [DAYS],
            one_time_keyboard=True,
            input_field_placeholder="<день>",
        ),
    )
    return DAY_SELECT


async def show(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        day = get_group_schedule(UNI_SITE + context.chat_data["group_link"])[
            update.message.text
        ]
    except KeyError:
        await update.message.reply_text(
            "Не знаю такого дня. Попробуй еще раз",
        )
        return
    except UniDownException:
        await uni_down_msg(update)
        return
    logger.log(logging.INFO, "Day  %s", update.message.text)
    await update.message.reply_text(
        f'Спасибо за обращение! Расписание на день "{update.message.text}":\n\n{pretty_day(day)}'
    )
    await update.message.reply_text(
        "Для нового запроса напиши /another. Если интересны те же параметры группы/факультета, набери /same. Для выхода пиши /quit\n"
        "Если расписание не отобразилось, то, скорее всего, бот еще не знает, как отображать расписание с вашего факультета."
    )
    return DONE


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("До встречи!", reply_markup=ReplyKeyboardRemove())
    return ConversationHandler.END


# https://github.com/python-telegram-bot/python-telegram-bot/blob/master/examples/chatmemberbot.py
def extract_status_change(
    chat_member_update: ChatMemberUpdated,
) -> Optional[Tuple[bool, bool]]:
    """Takes a ChatMemberUpdated instance and extracts whether the 'old_chat_member' was a member
    of the chat and whether the 'new_chat_member' is a member of the chat. Returns None, if
    the status didn't change.
    """
    diff = chat_member_update.difference()
    status_change = diff.get("status")
    old_is_member, new_is_member = diff.get("is_member", (None, None))

    if status_change is None:
        return None

    old_status, new_status = status_change
    was_member = old_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (old_status == ChatMember.RESTRICTED and old_is_member is True)
    is_member = new_status in [
        ChatMember.MEMBER,
        ChatMember.OWNER,
        ChatMember.ADMINISTRATOR,
    ] or (new_status == ChatMember.RESTRICTED and new_is_member is True)

    return was_member, is_member


async def track_chats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Tracks the chats the bot is in."""
    result = extract_status_change(update.my_chat_member)
    if result is None:
        return
    was_member, is_member = result

    # Let's check who is responsible for the change
    cause_name = update.effective_user.full_name

    # Handle chat types differently:
    chat = update.effective_chat
    if chat.type == Chat.PRIVATE:
        if not was_member and is_member:
            # This may not be really needed in practice because most clients will automatically
            # send a /start command after the user unblocks the bot, and start_private_chat()
            # will add the user to "user_ids".
            # We're including this here for the sake of the example.
            logger.info("%s unblocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s blocked the bot", cause_name)
            context.bot_data.setdefault("user_ids", set()).discard(chat.id)
    elif chat.type in [Chat.GROUP, Chat.SUPERGROUP]:
        if not was_member and is_member:
            logger.info("%s added the bot to the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).add(chat.id)
        elif was_member and not is_member:
            logger.info("%s removed the bot from the group %s", cause_name, chat.title)
            context.bot_data.setdefault("group_ids", set()).discard(chat.id)
    elif not was_member and is_member:
        logger.info("%s added the bot to the channel %s", cause_name, chat.title)
        context.bot_data.setdefault("channel_ids", set()).add(chat.id)
    elif was_member and not is_member:
        logger.info("%s removed the bot from the channel %s", cause_name, chat.title)
        context.bot_data.setdefault("channel_ids", set()).discard(chat.id)


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
                CommandHandler("same", same),
                CommandHandler("quit", cancel),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    application.add_handler(
        ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    application.run_polling()
