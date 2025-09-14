import json

from index import handler
from utils import get_triggers

if __name__ == '__main__':
    handler({
        'body': json.dumps({'update_id': 149165245, 'message': {'message_id': 557, 'from': {'id': 164671585, 'is_bot': False, 'first_name': 'Gleb', 'last_name': 'Yuzhakov', 'username': 'yugle7', 'language_code': 'ru'}, 'chat': {'id': 164671585, 'first_name': 'Gleb', 'last_name': 'Yuzhakov', 'username': 'yugle7', 'type': 'private'}, 'date': 1757884140, 'text': 'создавай 19 пт напоминай 8 сб'}})
    })

    for t in get_triggers('''
        создавай 19 пт напоминай 8 сб
    ''').items():
        print(t)


