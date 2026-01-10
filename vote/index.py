import json

import db


def handler(event, context=None):
    body = json.loads(event["body"])

    answer = body.get("poll_answer")

    if not answer:
        result = "not"
    else:
        try:
            poll_id = answer["poll_id"]
            votes = answer["option_ids"]

            user_id = answer["user"]["id"]
            username = answer["user"].get("username", user_id)

            db.add_vote(poll_id, user_id, username, votes)
            result = "ok"

        except Exception as err:
            print(err)
            result = "fail"

    return {"statusCode": 200, "body": result}
