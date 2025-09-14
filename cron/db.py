# import ydb
import ydb.iam

import os
import json
from time import time

import dotenv

from utils import get_next

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


def read_crons(key):
    now = int(time())
    crons = execute(f'SELECT id, group_id, poll, trigger FROM crons WHERE {key}<={now} AND {key}>0;')
    for c in crons:
        c['trigger'] = json.loads(c['trigger'])
        c['poll'] = json.loads(c['poll'])
    return crons


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


def update_next(cron, key):
    t = min(get_next(t) for t in cron['trigger'][key])
    execute(f"UPDATE crons SET {key}={t} WHERE id={cron['id']};")
