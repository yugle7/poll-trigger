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


def safe(func):
    def wrapper(*args):
        try:
            return func(*args)
        except Exception as e:
            print(f"{func.__name__}: {e}")
            return None

    return wrapper


@safe
def get_start_date(cron):
    trigger = cron["triggers"]["start"]
    start = datetime.now() + timedelta(hours=cron["time_zone"])

    if "weekday" in trigger:
        days = (trigger["weekday"] - start.weekday()) % 7
        start += timedelta(days=days)
    elif "hour" not in trigger:
        return ""
    elif trigger["hour"] <= start.hour:
        start += timedelta(days=1)

    return f"{start.day} {MONTHS[start.month - 1]}"


def get_when(trigger, time_zone):
    if "hour" not in trigger:
        return 0

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
