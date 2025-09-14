import db
import tg


def create_poll(cron):
    poll, created = tg.create_poll(cron['group_id'], cron['poll'])

    db.add_poll(poll['id'], cron['group_id'], cron['id'], created)
    db.edit_trigger(cron, 'create')


def notify_poll(cron):
    users = db.get_users(cron['id'])

    if users:
        text = ', '.join('@' + u.decode() for u in users)
        tg.send_message(cron['group_id'], f'отмечайтесь в опросе {text}')

    db.edit_trigger(cron, 'notify')


def handler(event=None, context=None):
    crons = db.read_crons('create')
    for c in crons:
        create_poll(c)

    crons = db.read_crons('notify')
    for c in crons:
        notify_poll(c)

    return {'statusCode': 200, 'body': 'ok'}
