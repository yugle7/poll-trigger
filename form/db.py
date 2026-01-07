import ydb
import ydb.iam

from cityhash import CityHash64

import os
import json

import dotenv

dotenv.load_dotenv()

driver = ydb.Driver(
    endpoint=os.getenv("YDB_ENDPOINT"),
    database=os.getenv("YDB_DATABASE"),
    # credentials=ydb.AuthTokenCredentials(os.getenv('IAM_TOKEN')),
    credentials=ydb.iam.MetadataUrlCredentials(),
)

driver.wait(fail_fast=True, timeout=5)

pool = ydb.SessionPool(driver)

settings = ydb.BaseRequestSettings().with_timeout(3).with_operation_timeout(2)


def execute(yql):
    def wrapper(session):
        try:
            res = session.transaction().execute(yql, commit_tx=True, settings=settings)
            return res[0].rows if len(res) else []

        except Exception as e:
            print(e)
            return []

    print(yql)
    return pool.retry_operation_sync(wrapper)


def read_data(user_id):
    forms = execute(f"SELECT form FROM forms WHERE user_id={user_id};")
    chats = execute(f"SELECT chat FROM chats WHERE user_id={user_id};")

    return {
        "forms": [json.loads(q.get("form")) for q in forms],
        "chats": [json.loads(q.get("chat")) for q in chats],
    }
