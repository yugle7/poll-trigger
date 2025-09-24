import db
import tg


def create_poll(cron):
    res = tg.create_poll(cron['group_id'], cron['thread_id'], cron['poll'])
    if res:
        db.add_poll(res['poll']['id'], cron['group_id'], cron['thread_id'], cron['id'], res['date'])
        db.update_next(cron, 'create')


def notify_poll(cron):
    users = db.get_users(cron['id'])
    if users:
        text = ', '.join('@' + u.decode() for u in users)
        tg.show_message(cron['group_id'], cron['thread_id'], f'Отмечайтесь в опросе {text}')
    db.update_next(cron, 'notify')


def handler(event=None, context=None):
    crons = db.read_crons('create')
    for c in crons:
        create_poll(c)

    crons = db.read_crons('notify')
    for c in crons:
        notify_poll(c)

    return {'statusCode': 200, 'body': 'ok'}
