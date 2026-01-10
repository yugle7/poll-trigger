from datetime import datetime, timedelta

MONTHS = [
    "янв",
    "фев",
    "мар",
    "апр",
    "май",
    "июн",
    "июл",
    "авг",
    "сен",
    "окт",
    "ноя",
    "дек",
]


def get_start_date(cron):
    triggers = cron["triggers"]
    days = (triggers["start"]["weekday"] - triggers["create"]["weekday"]) % 7
    start = datetime.now() + timedelta(days=days, hours=cron["time_zone"])
    return f"{start.day} {MONTHS[start.month - 1]}"


def get_when(trigger, time_zone):
    time_zone = timedelta(hours=time_zone)
    now = datetime.now() + time_zone
    t = now.replace(hour=trigger["hour"], minute=0, second=0, microsecond=0)

    days = (trigger["weekday"] - t.weekday()) % 7
    if days:
        t += timedelta(days=days)
    elif t <= now:
        t += timedelta(days=7)

    return int((t - time_zone).timestamp())
