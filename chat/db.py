import ydb.iam

import os

import dotenv

from cityhash import CityHash64


def get_id(a, b):
    return CityHash64(str(a) + " " + str(b).lower().strip())


dotenv.load_dotenv()

driver = ydb.Driver(
    endpoint=os.getenv("YDB_ENDPOINT"),
    database=os.getenv("YDB_DATABASE"),
    credentials=ydb.AuthTokenCredentials(os.getenv("IAM_TOKEN")),
    # credentials=ydb.iam.MetadataUrlCredentials()
)

driver.wait(fail_fast=True, timeout=10)

pool = ydb.SessionPool(driver)

settings = ydb.BaseRequestSettings().with_timeout(10).with_operation_timeout(8)


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


def add_vote(poll_id, user_id, username, votes):
    id = get_id(poll_id, user_id)
    if votes:
        vote = sum(1 << v for v in votes)
        execute(
            f'INSERT INTO votes (id, poll_id, username, vote) VALUES ({id}, "{poll_id}", "{username}", {vote});'
        )
    else:
        execute(f"DELETE FROM votes WHERE id={id};")
