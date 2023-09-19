import os
import logging
from typing import Optional, Tuple
import sqlite3
from contextlib import closing

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

from myshared import UniDownException, UNI_PAGE
from parse_places import get_places
from parse_groups import get_groups
from parse_group_schedule import get_group_schedule, DAYS, pretty_day
from about_teacher import teachers_search

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logging.getLogger("httpx").setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

DB_FILE = "tgbotdata.db"


def connect_and_init_db() -> sqlite3.Connection:
    con = sqlite3.connect(DB_FILE)
    with closing(con.cursor()) as cur:
        cur.execute("CREATE TABLE IF NOT EXISTS place (name, url)")
        cur.execute("CREATE TABLE IF NOT EXISTS study_group (name, url, place_id)")
        cur.execute("CREATE TABLE IF NOT EXISTS teacher (name, sguid)")
        cur.execute(
            "CREATE TABLE IF NOT EXISTS schedule_entry (discipline_name, type, week, location, auditorium, day, teacher_name, info, count)"
        )
        cur.execute(
            "CREATE TABLE IF NOT EXISTS study_group_to_schedule_entry (study_group_id, schedule_entry_id)"
        )
    return con


def db_update_places(con: sqlite3.Connection):
    places = get_places()
    with closing(con.cursor()) as cur:
        cur.executemany("INSERT INTO place VALUES (?, ?)", places.items())
        con.commit()


def db_get_places(con: sqlite3.Connection) -> list[tuple[str, str]]:
    with closing(con.cursor()) as cur:
        return cur.execute("SELECT place.name, place.url FROM place").fetchall()


def db_update_groups(place: str, con: sqlite3.Connection):
    with closing(con.cursor()) as cur:
        place_id, place_url = cur.execute(
            "SELECT place.rowid, place.url FROM place WHERE place.name = ?",
            (place,),
        ).fetchone()
        groups = get_groups(UNI_PAGE + place_url)
        cur.executemany(
            "INSERT INTO study_group VALUES (?, ?, ?)",
            [(name, url, place_id) for name, url in groups.items()],
        )
        con.commit()


def db_get_groups(place: str, con: sqlite3.Connection) -> list[tuple[str, str, int]]:
    with closing(con.cursor()) as cur:
        return cur.execute(
            "SELECT study_group.name, study_group.url, study_group.place_id FROM study_group\n"
            "JOIN place BY study_group.place_id = place.rowid\n"
            "WHERE place.name = ?",
            place,
        ).fetchall()


(
    START,
    SELECT_STEP,
    FAC_SELECT,
    TEACHER_SELECT,
    EXACT_TEACHER_SELECT,
    GROUP_SELECT,
    DAY_SELECT,
    DONE,
) = range(8)

QUERY_TEACHER, QUERY_GROUP = range(2)


# FeelsBadMan
async def uni_down_msg(update: Update):
    logger.log(logging.WARN, "Site is unreachable again...")
    await update.message.reply_text(
        "Сайт университета не отвечает. Возможно, бот сейчас находится во временной блокировке..."
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Этот бот умеет получать и выводить расписание СГУ.\n"
        "Просьба: не используйте его слишком часто, иначе ему прилетит блокировка с сайта СГУ.\n"
        "ℹ️ Если бот перестал отвечать посреди запроса - скорее всего его разработчик посеял баг и из-за этого бот со спокойной совестью прилег с ошибкой : )",
        reply_markup=ReplyKeyboardMarkup(
            [["Хорошо."]],
            one_time_keyboard=True,
        ),
    )
    return START


async def selection_step(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "По какому параметру хочешь посмотреть расписание?",
        reply_markup=ReplyKeyboardMarkup(
            [["Преподаватель"], ["Группа"]],
            one_time_keyboard=True,
            input_field_placeholder="<факультет>",
        ),
    )
    return SELECT_STEP


async def fac_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["current_query"] = QUERY_GROUP
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
        return


async def teacher_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data["current_query"] = QUERY_TEACHER
    await update.message.reply_text("Напиши фамилию преподавателя.")
    return TEACHER_SELECT


async def exact_teacher_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.chat_data["teachers"] = teachers_search(update.message.text)
    except UniDownException:
        await uni_down_msg(update)
        return
    await update.message.reply_text(
        "Выбери из списка:",
        reply_markup=ReplyKeyboardMarkup(
            [[fio] for fio in map(lambda t: t["fio"], context.chat_data["teachers"])],
            one_time_keyboard=True,
            input_field_placeholder="<преподаватель>",
        ),
    )
    return EXACT_TEACHER_SELECT


async def group_select(update: Update, context: ContextTypes.DEFAULT_TYPE):
    facs = get_faculs()
    if update.message.text not in facs:
        await update.message.reply_text(
            "⚠️ Не знаю такого факультета. Попробуй еще раз"
        )
        return
    context.chat_data["fac_link"] = facs[update.message.text]
    logger.log(
        logging.INFO,
        "Faculty %s, link %s",
        update.message.text,
        context.chat_data["fac_link"],
    )
    try:
        context.chat_data["groups"] = get_groups(
            UNI_SITE + context.chat_data["fac_link"]
        )
        await update.message.reply_text(
            (
                f"✅ Выбранный факультет: {update.message.text}, адрес {context.chat_data['fac_link']}\n"
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
    day_markup = ReplyKeyboardMarkup(
        [DAYS],
        one_time_keyboard=True,
        input_field_placeholder="<день>",
    )
    if context.chat_data["current_query"] == QUERY_GROUP:
        if update.message.text not in context.chat_data["groups"]:
            await update.message.reply_text(
                "⚠️ Не знаю такой группы. Попробуй еще раз",
            )
            return
        context.chat_data["query_link"] = context.chat_data["groups"][
            update.message.text
        ]
        logger.log(
            logging.INFO,
            "Group %s, link %s",
            update.message.text,
            context.chat_data["query_link"],
        )
        await update.message.reply_text(
            f"✅ Выбранная группа: {update.message.text}\nВыберите день.",
            reply_markup=day_markup,
        )
    else:
        teacher = [
            teacher
            for teacher in context.chat_data["teachers"]
            if teacher["fio"] == update.message.text
        ]
        if len(teacher) == 0:
            await update.message.reply_text(
                "⚠️ Не знаю такого преподавателя. Попробуй еще раз",
            )
            return
        context.chat_data["teacher_id"] = teacher[0]["id"][2:]  # omit 'id' in string
        logger.log(
            logging.INFO,
            "Teacher %s, id %s",
            update.message.text,
            context.chat_data["teacher_id"],
        )
        context.chat_data["query_link"] = (
            "/schedule/teacher/" + context.chat_data["teacher_id"]
        )
        await update.message.reply_text(
            f"✅ Выбранный преподаватель: {update.message.text}\nВыберите день.",
            reply_markup=day_markup,
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
    if update.message.text not in DAYS:
        await update.message.reply_text(
            "⚠️ Не знаю такого дня. Попробуй еще раз",
        )
        return
    try:
        day = get_group_schedule(UNI_SITE + context.chat_data["query_link"])[
            update.message.text
        ]
    except UniDownException:
        await uni_down_msg(update)
        return
    logger.log(logging.INFO, "Day %s", update.message.text)
    await update.message.reply_text(
        f'🆗 Спасибо за обращение! Расписание на день "{update.message.text}":\n\n{pretty_day(day)}'
    )
    await update.message.reply_text(
        'ℹ️ Для нового запроса напиши "запрос". Если нужно получить расписание на другой день с теми же параметрами, набери "ещё".\n'
        "Если расписание не отобразилось, то, скорее всего, бот еще не знает, как отображать расписание по твоему запросу.",
        reply_markup=ReplyKeyboardMarkup([["запрос"], ["ещё"]], one_time_keyboard=True),
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
            START: [MessageHandler(filters.Text(["Хорошо."]), selection_step)],
            SELECT_STEP: [
                MessageHandler(filters.Text(["Преподаватель"]), teacher_select),
                MessageHandler(filters.Text(["Группа"]), fac_select),
            ],
            TEACHER_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), exact_teacher_select)
            ],
            EXACT_TEACHER_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), day_select)
            ],
            FAC_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), group_select)
            ],
            GROUP_SELECT: [
                MessageHandler(filters.TEXT & (~filters.COMMAND), day_select)
            ],
            DAY_SELECT: [MessageHandler(filters.TEXT & (~filters.COMMAND), show)],
            DONE: [
                MessageHandler(filters.Text(["запрос"]), selection_step),
                MessageHandler(filters.Text(["ещё"]), same),
            ],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)

    application.add_handler(
        ChatMemberHandler(track_chats, ChatMemberHandler.MY_CHAT_MEMBER)
    )

    application.run_polling()
