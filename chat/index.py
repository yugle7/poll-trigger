import json

import db
import tg

BOT_NAME = "polltriggerbot"


def handle(body):
    answer = body.get("poll_answer")

    if answer:
        poll_id = answer["poll_id"]
        votes = answer["option_ids"]

        user_id = answer["user"]["id"]
        username = answer["user"].get("username", user_id)

        db.add_vote(poll_id, user_id, username, votes)
        return "проголосовал"

    message = body.get("message")
    if not message:
        return "нет сообщения"

    user_id = message["from"]["id"]
    chat_id = message["chat"]["id"]

    text = message.get("text")

    if chat_id != user_id:
        group_id = chat_id

        if not text or not text.startswith("/"):
            return "не команда"

        if "@" in text and text.endswith("@polltriggerbot"):
            return "не ко мне"

        if not tg.is_admin(user_id, group_id):
            return "не админ"

        thread_id = message.get("message_thread_id")

        if not db.get_user(user_id):
            tg.show_message(
                group_id, thread_id, "Сначала заведите личную переписку со мной"
            )
            return "нет чата со мной"

        group = message["chat"]["title"]
        reply = message.get("reply_to_message")
        if thread_id and reply:
            thread = reply["forum_topic_created"]["name"]
        else:
            thread = None

        if "/attach" in text:
            db.attach_chat(user_id, group_id, group, thread_id, thread)
            return "связал"

        if "/detach" in text:
            db.detach_chat(user_id, group_id, thread_id)
            return "отвязал"

        return "не понял"

    elif text == "/start":
        if db.create_user(user_id):
            answer = "Отлично! Рад вас видеть!\n\nЧтобы создавать здесь опросы для вашего чата, добавьте меня в тот чат и свяжите меня с ним, отправив туда команду /attach"
        else:
            answer = "Привет! Отправьте команду /attach в тот чат, где вы собираетесь создавать опросы"

        tg.send_message(user_id, answer)
        return "старт"

    return "тоже успех"


def handler(event, context=None):
    body = json.loads(event["body"])

    try:
        return {"statusCode": 200, "body": handle(body)}

    except Exception as e:
        print(e)

    return {"statusCode": 200, "body": "fail"}
