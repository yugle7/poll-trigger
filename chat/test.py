# import json

# from index import handler
from utils import get_triggers

if __name__ == '__main__':
    # handler({
    #     'body': json.dumps({'update_id': 597531877, 'message': {'message_id': 148, 'from': {'id': 164671585, 'is_bot': False, 'first_name': 'Gleb', 'last_name': 'Yuzhakov', 'username': 'yugle7', 'language_code': 'ru'}, 'chat': {'id': 164671585, 'first_name': 'Gleb', 'last_name': 'Yuzhakov', 'username': 'yugle7', 'type': 'private'}, 'date': 1757845921, 'text': 'День рождения у Платона 15 января 11\nДень рождения у Вити Черного 29 мая 23\nДень рождения у Эмиля 08 декабря 8'}})
    # })

    for t in get_triggers('''
        создавай 19 пт напоминай 8 сб
    ''').items():
        print(t)


