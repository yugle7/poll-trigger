import json

import tg
import db

from utils import get_id, what, shift, get_command, get_changes, clear_text


def handler(event, context=None):
    body = json.loads(event['body'])
    print('body:', body)

    try:
        answer = handle(body)

    except Exception as err:
        print(err)
        answer = 'фатальная ошибка'

    return {'statusCode': 200, 'body': answer}


def send_answer(text, chat_id, message_id, edited):
    print(text)

    answer_id = edited and db.get_answer_id(chat_id, message_id)

    if answer_id:
        if not tg.edit_message(chat_id, answer_id, text):
            tg.delete_message(chat_id, answer_id)
            answer_id = tg.send_message(chat_id, text)
            db.edit_answer_id(chat_id, message_id, answer_id)
    else:
        answer_id = tg.send_message(chat_id, text)
        db.save_answer_id(chat_id, message_id, answer_id)


def create_poll(cron):
    poll, created = tg.create_poll(cron['group_id'], cron['poll'])
    db.add_poll(poll['id'], cron['group_id'], cron['id'], created)


def notify_poll(cron):
    users = db.get_users(cron['id'])
    if users:
        text = ', '.join('@' + u.decode() for u in users)
        tg.send_message(cron['group_id'], f'отмечайтесь в опросе {text}')


def handle(body):
    answer = body.get('poll_answer')
    if answer:
        poll_id = answer['poll_id']
        votes = answer['option_ids']

        user_id = answer['user']['id']
        username = answer['user']['username']

        db.add_vote(poll_id, user_id, username, votes)
        return 'проголосовал в опросе'

    message = body.get('message') or body.get('edited_message')
    if not message:
        return 'нет сообщения'

    user_id = message['from']['id']
    chat_id = message['chat']['id']

    try:
        if chat_id != user_id:
            text = message.get('text')
            if not text or '@' not in text:
                return 'не ко мне'

            if not db.get_user(user_id):
                tg.send_message(chat_id, 'сначала заведите личную переписку со мной')
                return 'не узнал'

            answer = mention_in_text(user_id, chat_id)

        else:
            poll = message.get('poll')
            if poll:
                answer = poll_message(user_id, poll, 'forward_origin' in message)
            else:
                text = message.get('text')
                if not text:
                    return 'нет текста'

                if '/start' in text:
                    answer = db.create_user(user_id)
                else:
                    text = clear_text(text)

                    reply = message.get('reply_to_message')
                    if reply:
                        poll = reply.get('poll')
                        if not poll:
                            answer = 'это ответ не на опрос'
                        else:
                            answer = reply_to_poll(user_id, poll, text)
                    else:
                        answer = text_message(user_id, text)
    except Exception as err:
        print(err)
        answer = 'что\\-то пошло не так'

    if not answer:
        return 'тоже успех'

    send_answer(answer, user_id, message['message_id'], 'edited_message' in body)
    return answer


def mention_in_text(user_id, group_id):
    title = tg.get_chat(group_id)['title']

    if not tg.is_admin(user_id, group_id):
        return f'у вас не хватает прав, чтобы создавать опросы в группе` {title}`, станьте сначала в ней администратором'

    db.update_user({'id': user_id, 'group_id': group_id})
    return f'теперь вы можете здесь создавать опросы и задавать время, когда их создавать в группе` {title} `и когда напоминать в них отмечаться'


def get_group_id(user, poll=None):
    group_id = poll and db.get_group_id(poll['id'])
    if group_id:
        user['group_id'] = group_id
        return group_id

    if user['group_id'] and not tg.is_admin(user['id'], user['group_id']):
        db.reset_user(user['id'])
        return None

    return user['group_id']


def poll_message(user_id, poll, forwarded):
    user = db.get_user(user_id)

    group_id = get_group_id(user, forwarded and poll)
    if not group_id:
        return 'вижу опрос, но не знаю с какой группой его связать'

    poll['options'] = [q['text'].strip() for q in poll['options']]
    poll = {k: poll[k] for k in ['question', 'options', 'is_anonymous', 'allows_multiple_answers']}

    cron_id = get_id(group_id, poll['question'])

    user['cron_id'] = cron_id
    db.update_user(user)

    cron = db.get_cron(cron_id)
    if cron:
        cron['poll'] = poll

        db.edit_cron(cron)
        return what(cron, user['shift'])

    cron = {
        'id': cron_id,
        'poll': poll,
        'group_id': group_id,
        'trigger': {'create': [], 'notify': []}
    }
    db.create_cron(cron)

    title = tg.get_chat(group_id)['title']
    return f'я связал этот опрос с группой` {title}`'


def reply_to_poll(user_id, poll, text):
    user = db.get_user(user_id)

    group_id = get_group_id(user, poll)
    if not group_id:
        return f'сначала свяжите меня с какой\\-нибудь группой'

    cron_id = get_id(group_id, poll['question'])

    cron = db.get_cron(cron_id)
    if cron:
        if cron['poll'] != poll:
            cron['poll'] = poll
            db.edit_cron(cron)
    else:
        cron = {
            'id': cron_id,
            'poll': poll,
            'group_id': group_id,
            'trigger': {'create': [], 'notify': []}
        }
        db.create_cron(cron)

    user['cron_id'] = cron_id
    db.update_user(user)

    command = get_command(text)
    return text_to_cron(user, cron, command, text)


def text_message(user_id, text):
    user = db.get_user(user_id)

    group_id = get_group_id(user)
    if not group_id:
        return 'я многое могу, но сначала меня надо связать с группой'

    command = get_command(text)
    if command == 'show':
        crons = db.load_crons(group_id)
        if not crons:
            title = tg.get_chat(group_id)['title']
            return f'в группе` {title} `еще нет управляемых мной опросов'

        return '\n\n'.join(what(c, user['shift']) for c in crons)

    cron_id = user['cron_id']
    if not cron_id:
        return 'с каким опросом это сделать?'

    cron = db.get_cron(cron_id)
    return text_to_cron(user, cron, command, text)


def text_to_cron(user, cron, command, text):
    question = cron['poll']['question']

    if command == 'resume':
        if not cron['trigger']['create']:
            return f'у опроса` {question} `еще не задано время создания, чтобы его возобновлять'

        if cron.get('create'):
            return f'опрос` {question} `уже и так создавался'

        db.resume_cron(cron)
        return what(cron, user['shift'])

    if command == 'stop':
        if not cron.get('create'):
            return f'опрос` {question} `и так не создавался'

        db.stop_cron(cron)
        return what(cron, user['shift'])

    if command == 'delete':
        if cron.get('create') is None:
            return f'опрос` {question} `и так был удален'

        user['cron_id'] = None
        db.update_user(user)

        db.delete_cron(cron['id'])
        return f'опрос` {question} `удален'

    if command == 'create':
        return create_poll(cron)

    if command == 'notify':
        return notify_poll(cron)

    if command == 'change':
        changes = get_changes(text)
        if not changes:
            return f'не понял как опрос` {question} `нужно поменять'

        trigger = {'create': [], 'notify': []}
        for action, hour, weekday in changes:
            if action == 'create':
                trigger['create'].append(shift({'weekday': weekday, 'hour': hour}, -user['shift']))

            elif action == 'not create':
                cron['trigger']['create'] = trigger['create'] = []

            elif action == 'notify':
                trigger['notify'].append(shift({'weekday': weekday, 'hour': hour}, -user['shift']))

            elif action == 'not notify':
                cron['trigger']['notify'] = trigger['notify'] = []

        for k, t in trigger.items():
            if t:
                cron['trigger'][k] = t

        if 'create' not in cron:
            db.create_cron(cron)
        else:
            db.change_cron(cron)

        return what(cron, user['shift'])

    if command == 'show':
        return what(cron, user['shift'])

    return f'что мне сделать с опросом` {question}`?'
