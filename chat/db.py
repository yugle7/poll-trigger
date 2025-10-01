import ydb.iam

import os
import json

import dotenv

from utils import get_next, get_id

dotenv.load_dotenv()

driver = ydb.Driver(
    endpoint=os.getenv('YDB_ENDPOINT'),
    database=os.getenv('YDB_DATABASE'),
    credentials=ydb.AuthTokenCredentials(os.getenv('IAM_TOKEN'))
    # credentials=ydb.iam.MetadataUrlCredentials()
)

driver.wait(fail_fast=True, timeout=10)

pool = ydb.SessionPool(driver)

settings = ydb \
    .BaseRequestSettings() \
    .with_timeout(10) \
    .with_operation_timeout(8)


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


def add_vote(poll_id, user_id, username, votes):
    id = get_id(poll_id, user_id)
    if votes:
        vote = sum(1 << v for v in votes)
        execute(f'INSERT INTO votes (id, poll_id, username, vote) VALUES ({id}, "{poll_id}", "{username}", {vote});')
    else:
        execute(f'DELETE FROM votes WHERE id={id};')


def load_crons(group_id):
    crons = execute(f'SELECT * FROM crons WHERE group_id={group_id} and create>=0;')

    for c in crons:
        c['triggers'] = json.loads(c['triggers'])
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


def add_poll(id, group_id, thread_id, cron_id=None, created=None):
    execute(f'INSERT INTO polls (id, group_id, thread_id, cron_id, created) VALUES ("{id}", {group_id}, {thread_id or "NULL"}, {cron_id or "NULL"}, {created or "NULL"});')


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


def get_cron(id):
    res = execute(f'SELECT * FROM crons WHERE id={id};')
    if not res:
        return None
    cron = res[0]
    cron['triggers'] = json.loads(cron['triggers'])
    cron['poll'] = json.loads(cron['poll'])
    return cron


def get_user(id):
    res = execute(f'SELECT * FROM users WHERE id={id};')
    return res and res[0]


def create_user(id):
    res = execute(f'INSERT INTO users (id, time_zone) VALUES ({id}, 3) RETURNING id;')
    if res:
        return True

    reset_where({'id': id})
    return False


def set_time_zone(user_id, time_zone):
    execute(f'UPDATE users SET time_zone={time_zone} WHERE id={user_id};')


def set_cron_id(user):
    id = user['id']
    group_id = user['group_id'] or 'NULL'
    thread_id = user['thread_id'] or 'NULL'
    cron_id = user['cron_id'] or 'NULL'
    execute(f'UPDATE users SET cron_id={cron_id}, group_id={group_id}, thread_id={thread_id} WHERE id={id};')


def get_where(poll_id):
    res = execute(f'SELECT group_id, thread_id FROM polls WHERE id="{poll_id}";')
    return res and res[0]


def set_where(user_id, group_id, thread_id):
    execute(f'UPDATE users SET cron_id=NULL, group_id={group_id}, thread_id={thread_id or "NULL"} WHERE id={user_id};')


def reset_where(user):
    id = user['id']
    user['group_id'] = user['cron_id'] = user['thread_id'] = None
    execute(f'UPDATE users SET cron_id=NULL, group_id=NULL, thread_id=NULL WHERE id={id};')


def change_cron(cron):
    id = cron['id']
    triggers = cron['triggers']

    cron['create'] = create = min(get_next(t) for t in triggers['create']) if triggers['create'] else 0
    cron['notify'] = notify = min(get_next(t) for t in triggers['notify']) if triggers['notify'] else 0

    execute(f"UPDATE crons SET create={create}, notify={notify}, triggers='{json.dumps(triggers)}' WHERE id={id};")


def edit_cron(cron):
    id = cron['id']
    poll = cron['poll']
    execute(f"UPDATE crons SET poll='{json.dumps(poll)}' WHERE id={id};")


def create_cron(cron):
    id = cron['id']
    triggers = cron['triggers']
    poll = cron['poll']

    group_id = cron['group_id']
    thread_id = cron['thread_id'] or 'NULL'

    cron['create'] = create = min(get_next(t) for t in triggers['create']) if triggers['create'] else 0
    cron['notify'] = notify = min(get_next(t) for t in triggers['notify']) if triggers['notify'] else 0

    values = f"({id}, {group_id}, {thread_id}, '{json.dumps(poll, ensure_ascii=False)}', {create}, {notify}, '{json.dumps(triggers)}')"
    execute(f"INSERT INTO crons (id, group_id, thread_id, poll, create, notify, triggers) VALUES {values};")


def resume_cron(cron):
    id = cron['id']
    trigger = cron['triggers']

    cron['create'] = create = min(get_next(t) for t in trigger['create']) if trigger['create'] else 0
    cron['notify'] = notify = min(get_next(t) for t in trigger['notify']) if trigger['notify'] else 0

    execute(f"UPDATE crons SET create={create}, notify={notify} WHERE id={id};")


def stop_cron(cron):
    id = cron['id']
    cron['create'] = cron['notify'] = 0
    execute(f"UPDATE crons SET create=0, notify=0 WHERE id={id};")


def delete_cron(id):
    execute(f"DELETE FROM crons WHERE id={id};")
