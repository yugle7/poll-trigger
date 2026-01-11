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
    trigger = cron["triggers"]["start"]
    if not trigger:
        return ""

    now = datetime.now() + timedelta(hours=cron["time_zone"])
    start = now.replace(hour=trigger["hour"], minute=0, second=0, microsecond=0)

    if "weekday" in trigger:
        days = (trigger["weekday"] - start.weekday()) % 7
        start += timedelta(days=days)
    elif trigger["hour"] <= now.hour:
        start += timedelta(days=1)

    return f"{start.day} {MONTHS[start.month - 1]}"


def get_when(trigger, time_zone):
    time_zone = timedelta(hours=time_zone)
    now = datetime.now() + time_zone
    t = now.replace(hour=trigger["hour"], minute=0, second=0, microsecond=0)

    if "weekday" in trigger:
        days = (trigger["weekday"] - t.weekday()) % 7
        if days:
            t += timedelta(days=days)
        elif t <= now:
            t += timedelta(days=7)
    elif t <= now:
        t += timedelta(days=1)

    return int((t - time_zone).timestamp())
