import json
import re

import tg
import db

from utils import get_id, to_answer, get_command, get_triggers, get_text
from datetime import datetime


def handler(event, context=None):
    body = json.loads(event["body"])
    print("body:", body)

    try:
        answer = handle(body)

    except Exception as err:
        print(err)
        answer = "фатальная ошибка"

    return {"statusCode": 200, "body": answer}


def send_answer(text, user_id, message_id, edited):
    print(text)

    answer_id = edited and db.get_answer_id(user_id, message_id)

    if answer_id:
        if not tg.edit_message(user_id, answer_id, text):
            tg.delete_message(user_id, answer_id)
            answer_id = tg.send_message(user_id, text)
            db.edit_answer_id(user_id, message_id, answer_id)
    else:
        answer_id = tg.send_message(user_id, text)
        db.save_answer_id(user_id, message_id, answer_id)


def create_poll(cron):
    res = tg.create_poll(cron["group_id"], cron["thread_id"], cron["poll"])
    if res:
        db.add_poll(
            res["poll"]["id"],
            cron["group_id"],
            cron["thread_id"],
            cron["id"],
            res["date"],
        )


def notify_poll(cron):
    users = db.get_users(cron["id"])
    if users:
        text = ", ".join("@" + u.decode() for u in users)
        tg.show_message(
            cron["group_id"], cron["thread_id"], f"Отмечайтесь в опросе {text}"
        )


def handle(body):
    answer = body.get("poll_answer")
    if answer:
        poll_id = answer["poll_id"]
        votes = answer["option_ids"]

        user_id = answer["user"]["id"]
        username = answer["user"].get("username", user_id)

        db.add_vote(poll_id, user_id, username, votes)
        return "проголосовал в опросе"

    message = body.get("message") or body.get("edited_message")
    if not message:
        return "нет сообщения"

    edited = "edited_message" in body
    forwarded = "forward_origin" in message

    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]

    text = message.get("text")

    try:
        if chat_id != user_id:
            if not text or "@" not in text:
                return "не ко мне"

            if not tg.is_admin(user_id, chat_id):
                return "не админ"

            thread_id = message.get("message_thread_id")

            if not db.get_user(user_id):
                tg.show_message(
                    chat_id, thread_id, "Сначала заведите личную переписку со мной"
                )
                return "не узнал"

            title = message["chat"]["title"]
            reply = message.get("reply_to_message")
            if thread_id and reply:
                topic = reply["forum_topic_created"]["name"]
                title = f"{title} ({topic})"

            answer = mention_in_text(user_id, chat_id, thread_id, title)

        elif text == "/start":
            if db.create_user(user_id):
                answer = "Отлично! Рад вас видеть!\n\nЧтобы создавать здесь опросы для вашей группы, добавьте меня в ту группу и свяжите меня с ней, отправив туда команду /start\n\nПо умолчанию время московское. Если захотите изменить его, то отправьте мне сколько сейчас времени у вас в формате 12:34"
            else:
                answer = "Привет! Я сейчас не привязан ни к какой группе, отправьте команду /start в той группе, где вы собираетесь создавать опросы?"
            tg.show_miniapp_button(user_id, "мои опросы")
        elif text and re.fullmatch(r"\d+:\d+", text):
            answer = set_time_zone(user_id, text)

        else:
            poll = message.get("poll")

            user = db.get_user(user_id)
            get_where(user, forwarded and poll)

            if not user["group_id"]:
                answer = "Сначала свяжите меня с какой-нибудь группой"
            else:
                if poll:
                    answer = poll_message(user, poll)
                elif not text:
                    return "нет текста"
                else:
                    text = get_text(text)

                    reply = message.get("reply_to_message")
                    if reply:
                        poll = reply.get("poll")
                        if not poll:
                            answer = "Это ответ не на опрос"
                        else:
                            answer = reply_to_poll(user, poll, text)
                    else:
                        answer = text_message(user, text)

    except Exception as err:
        print(err)
        answer = "Что-то пошло не так"

    if not answer:
        return "тоже успех"

    send_answer(answer, user_id, message["message_id"], edited)
    return answer


def mention_in_text(user_id, group_id, thread_id, where):
    if not tg.is_admin(user_id, group_id):
        return f'У вас не хватает прав, чтобы создавать опросы в группе "{where}", станьте сначала в ней администратором'

    db.set_where(user_id, group_id, thread_id)
    return f'Теперь вы можете здесь создавать опросы и задавать время, когда их создавать в группе "{where}" и когда напоминать в них отмечаться'


def set_time_zone(user_id, text):
    h, m = map(int, text.split(":"))
    if not (0 <= h < 24 and 0 <= m < 60):
        return "Я не смог понять какое у вас время, ожидаю формат 12:34"

    now = datetime.now()
    time_zone = (24 + h + m / 60 - now.hour - now.minute / 60) % 24
    time_zone = int(time_zone + 0.5)
    db.set_time_zone(user_id, time_zone)

    return f"Установлен часовой пояс UTC+{time_zone}"


def get_where(user, poll=None):
    if poll:
        where = db.get_where(poll["id"])
        if where:
            if tg.is_admin(user["id"], where["group_id"]):
                user["group_id"] = where["group_id"]
                user["thread_id"] = where["thread_id"]
                return

    if user["group_id"] and not tg.is_admin(user["id"], user["group_id"]):
        db.reset_where(user)


def poll_message(user, poll):
    poll["options"] = [q["text"].strip() for q in poll["options"]]
    poll = {
        k: poll[k]
        for k in ["question", "options", "is_anonymous", "allows_multiple_answers"]
    }

    where_id = get_id(user["group_id"], user["thread_id"])
    user["cron_id"] = get_id(where_id, poll["question"])
    db.set_cron_id(user)

    cron = db.get_cron(user["cron_id"])
    if cron:
        cron["poll"] = poll

        db.edit_cron(cron)
        return to_answer(cron, user)

    cron = {
        "id": user["cron_id"],
        "poll": poll,
        "group_id": user["group_id"],
        "thread_id": user["thread_id"],
        "triggers": {"create": [], "notify": []},
    }
    db.create_cron(cron)

    title = tg.get_chat(user["group_id"])["title"]
    return f'Я связал этот опрос с группой "{title}"'


def reply_to_poll(user, poll, text):
    where_id = get_id(user["group_id"], user["thread_id"])
    user["cron_id"] = get_id(where_id, poll["question"])
    db.set_cron_id(user)

    cron = db.get_cron(user["cron_id"])
    if cron:
        if cron["poll"] != poll:
            cron["poll"] = poll
            db.edit_cron(cron)
    else:
        cron = {
            "id": user["cron_id"],
            "poll": poll,
            "group_id": user["group_id"],
            "thread_id": user["thread_id"],
            "triggers": {"create": [], "notify": []},
        }
        db.create_cron(cron)

    command = get_command(text)
    return text_to_cron(user, cron, command, text)


def text_message(user, text):
    command = get_command(text)
    if command == "show":
        crons = db.load_crons(user["group_id"])
        if not crons:
            title = tg.get_chat(user["group_id"])["title"]
            return f'В группе "{title}" еще нет управляемых мной опросов'

        return "\n\n".join(to_answer(c, user) for c in crons)

    if not user["cron_id"]:
        return "С каким опросом это сделать?"

    cron = db.get_cron(user["cron_id"])
    return text_to_cron(user, cron, command, text)


def text_to_cron(user, cron, command, text):
    question = cron["poll"]["question"]

    if command == "resume":
        if not cron["triggers"]["create"]:
            return f'У опроса "{question}" еще не задано время создания, чтобы его возобновлять'

        if cron.get("create"):
            return f'Опрос "{question}" уже и так создавался'

        db.resume_cron(cron)
        return to_answer(cron, user)

    if command == "stop":
        if not cron.get("create"):
            return f'Опрос "{question}" и так не создавался'

        db.stop_cron(cron)
        return to_answer(cron, user)

    if command == "delete":
        if cron.get("create") is None:
            return f'Опрос "{question}" и так был удален'

        user["cron_id"] = None
        db.set_cron_id(user)

        db.delete_cron(cron["id"])
        return f'Опрос "{question}" удален'

    if command == "create":
        return create_poll(cron)

    if command == "notify":
        return notify_poll(cron)

    if command == "change":
        triggers = get_triggers(text)
        if not triggers:
            return f'Не понял как опрос "{question}" нужно поменять'

        for key, triggers in triggers.items():
            for t in triggers:
                t["time_zone"] = user["time_zone"]
            cron["triggers"][key] = triggers

        if "create" not in cron:
            db.create_cron(cron)
        else:
            db.change_cron(cron)

        return to_answer(cron, user)

    if command == "show":
        return to_answer(cron, user)

    return f'Что мне сделать с опросом "{question}"?'
