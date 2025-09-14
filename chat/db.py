import ydb
import ydb.iam

import os
import json
from time import time

import dotenv

from utils import next, get_id

dotenv.load_dotenv()

driver = ydb.Driver(
    endpoint=os.getenv('YDB_ENDPOINT'),
    database=os.getenv('YDB_DATABASE'),
    credentials=ydb.AuthTokenCredentials(os.getenv('IAM_TOKEN'))
    # credentials=ydb.iam.MetadataUrlCredentials()
)

driver.wait(fail_fast=True, timeout=5)

pool = ydb.SessionPool(driver)

settings = ydb \
    .BaseRequestSettings() \
    .with_timeout(3) \
    .with_operation_timeout(2)


def execute(yql):
    def wrapper(session):
        try:
            res = session.transaction().execute(
                yql,
                commit_tx=True,
                settings=settings
            )
            return res[0].rows if len(res) else []

        except Exception as e:
            print(e)
            return []

    print(yql)
    return pool.retry_operation_sync(wrapper)


def to_bin(values):
    return sum(1 << v for v in values)


def add_vote(poll_id, user_id, username, votes):
    id = get_id(poll_id, user_id)
    if votes:
        execute(f'INSERT INTO votes (id, poll_id, username, vote) VALUES ({id}, "{poll_id}", "{username}", {to_bin(votes)});')
    else:
        execute(f'DELETE FROM votes WHERE id={id};')


def load_crons(group_id):
    crons = execute(f'SELECT * FROM crons WHERE group_id={group_id} and create>=0;')

    for c in crons:
        c['trigger'] = json.loads(c['trigger'])
        c['poll'] = json.loads(c['poll'])

    return crons


def read_crons(key):
    now = int(time())
    crons = execute(f'SELECT id, group_id, poll, trigger FROM crons WHERE {key}<={now} AND {key}>0;')
    for c in crons:
        c['trigger'] = json.loads(c['trigger'])
        c['poll'] = json.loads(c['poll'])
    return crons


def save_answer_id(chat_id, message_id, answer_id):
    id = get_id(chat_id, message_id)
    execute(f'INSERT INTO messages (id, answer_id) VALUES ({id}, {answer_id or "NULL"});')


def edit_answer_id(chat_id, message_id, answer_id):
    id = get_id(chat_id, message_id)
    execute(f'UPDATE messages SET answer_id={answer_id or "NULL"} WHERE id={id};')


def delete_answer_id(chat_id, message_id):
    id = get_id(chat_id, message_id)
    execute(f'DELETE FROM messages WHERE id={id};')


def get_answer_id(chat_id, message_id):
    id = get_id(chat_id, message_id)
    res = execute(f'SELECT answer_id FROM messages WHERE id={id};')
    return res[0].get('answer_id') if res else None


def add_poll(id, group_id, cron_id=None, created=None):
    execute(f'INSERT INTO polls (id, group_id, cron_id, created) VALUES ("{id}", {group_id}, {cron_id or "NULL"}, {created or "NULL"});')


def get_users(cron_id):
    polls = execute(f'SELECT id, created FROM polls WHERE cron_id={cron_id} ORDER BY created;')

    if len(polls) < 2:
        return []

    poll = polls.pop()
    res = execute(f'SELECT username FROM votes WHERE poll_id="{poll["id"].decode()}";')
    users = {u.get('username') for u in res}

    poll = polls.pop()
    res = execute(f'SELECT username FROM votes WHERE poll_id="{poll["id"].decode()}";')
    return {u.get('username') for u in res} - users


def edit_trigger(cron, key):
    t = min(next(t) for t in cron['trigger'][key])
    execute(f"UPDATE crons SET {key}={t} WHERE id={cron['id']};")


def get_group_id(poll_id):
    res = execute(f'SELECT group_id FROM polls WHERE id="{poll_id}";')
    return res and res[0].get('group_id')


def get_cron(id):
    res = execute(f'SELECT * FROM crons WHERE id={id};')
    if not res:
        return None
    cron = res[0]
    cron['trigger'] = json.loads(cron['trigger'])
    cron['poll'] = json.loads(cron['poll'])
    return cron


def get_user(id):
    res = execute(f'SELECT * FROM users WHERE id={id};')
    return res and res[0]


def create_user(id):
    res = execute(f'INSERT INTO users (id, shift) VALUES ({id}, 3) RETURNING id;')
    if res:
        return 'отлично\\! рад вас видеть\\! чтобы создавать здесь опросы для вашей группы, добавьте меня в ту группу и свяжите меня с ней, отправив туда сообщение @PollTriggerBot'

    update_user({'id': id})
    return 'привет\\! я сейчас не привязан ни к какой группе, давайте привяжемся и начнем создавать опросы\\?'


def update_user(user):
    id = user['id']
    cron_id = user.get('cron_id') or 'NULL'
    group_id = user.get('group_id') or 'NULL'

    execute(f'UPDATE users SET cron_id={cron_id}, group_id={group_id} WHERE id={id};')


def reset_user(id):
    execute(f'UPDATE users SET cron_id=NULL, group_id=NULL WHERE id={id};')


def change_cron(cron):
    id = cron['id']
    trigger = cron['trigger']

    cron['create'] = create = min(next(t) for t in trigger['create']) if trigger['create'] else 0
    cron['notify'] = notify = min(next(t) for t in trigger['notify']) if trigger['notify'] else 0

    execute(f"UPDATE crons SET create={create}, notify={notify}, trigger='{json.dumps(trigger)}' WHERE id={id};")


def edit_cron(cron):
    id = cron['id']
    poll = cron['poll']
    execute(f"UPDATE crons SET poll='{json.dumps(poll)}' WHERE id={id};")


def create_cron(cron):
    id = cron['id']
    trigger = cron['trigger']
    poll = cron['poll']
    group_id = cron['group_id']

    cron['create'] = create = min(next(t) for t in trigger['create']) if trigger['create'] else 0
    cron['notify'] = notify = min(next(t) for t in trigger['notify']) if trigger['notify'] else 0

    values = f"({id}, {group_id}, '{json.dumps(poll, ensure_ascii=False)}', {create}, {notify}, '{json.dumps(trigger)}')"
    execute(f"INSERT INTO crons (id, group_id, poll, create, notify, trigger) VALUES {values};")


def resume_cron(cron):
    id = cron['id']
    trigger = cron['trigger']

    cron['create'] = create = min(next(t) for t in trigger['create']) if trigger['create'] else 0
    cron['notify'] = notify = min(next(t) for t in trigger['notify']) if trigger['notify'] else 0

    execute(f"UPDATE crons SET create={create}, notify={notify} WHERE id={id};")


def stop_cron(cron):
    id = cron['id']
    cron['create'] = cron['notify'] = 0
    execute(f"UPDATE crons SET create=0, notify=0 WHERE id={id};")


def delete_cron(id):
    trigger = {'create': [], 'notify': []}
    execute(f"UPDATE crons SET create=NULL, notify=NULL, trigger='{json.dumps(trigger)}' WHERE id={id};")
