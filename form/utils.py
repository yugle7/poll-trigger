from datetime import datetime, timedelta

WEEKDAYS = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"]


def get_trigger(when):
    weekday, hour = when.lower().split()
    hour = int(hour.split(":")[0])
    weekday = WEEKDAYS.index(weekday)
    return {"hour": hour, "weekday": weekday}


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


def get_cron(form):
    group_id, thread_id = map(int, form["chat"].split())

    time_zone = form.get("time_zone", 3)
    start = get_trigger(form["start"])
    create = get_trigger(form["create"])
    notify = get_trigger(form["notify"])

    return {
        "group_id": group_id,
        "thread_id": thread_id,
        "poll": {
            "question": f"{form['what']} {form['start']} ({form['where']})",
            "options": [who for who in form["who"] if who],
            "is_anonymous": False,
            "allows_multiple_answers": False,
        },
        "create": get_when(create, time_zone),
        "notify": get_when(notify, time_zone),
        "triggers": {"create": create, "notify": notify, "start": start},
        "time_zone": time_zone,
    }
