from datetime import datetime, timedelta


def get_start_date(triggers, time_zone):
    time_zone = timedelta(hours=time_zone)
    days = (triggers["start"]["weekday"] - triggers["create"]["weekday"]) % 7
    start = datetime.now() + time_zone + timedelta(days=days)
    return start.strftime("DD.MM")


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
