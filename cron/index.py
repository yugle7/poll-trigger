import db
import tg
from utils import get_start_date


def create_poll(cron):
    poll = cron["poll"]
    poll["question"] += " - " + get_start_date(cron)
    res = tg.create_poll(cron["group_id"], cron["thread_id"], poll)
    if res:
        db.add_poll(
            res["poll"]["id"],
            cron["group_id"],
            cron["thread_id"],
            cron["id"],
            res["date"],
        )
        db.update_when(cron, "create")


def notify(username):
    if username.isdigit():
        return f"[user](tg://user?id={username.decode()})"
    return f"@{username.decode()}"


def notify_poll(cron):
    usernames = db.get_usernames(cron["id"])
    if usernames:
        text = ", ".join(notify(u) for u in usernames)
        tg.show_message(
            cron["group_id"], cron["thread_id"], f"Отмечайтесь в опросе {text}"
        )
    db.update_when(cron, "notify")


def handler(event=None, context=None):
    crons = db.read_crons("create")
    for c in crons:
        create_poll(c)

    crons = db.read_crons("notify")
    for c in crons:
        notify_poll(c)

    return {"statusCode": 200, "body": "ok"}
