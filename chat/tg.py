import json
import os

import requests
import re

import dotenv

dotenv.load_dotenv()

TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
API_GATEWAY_DOMAIN = os.getenv('API_GATEWAY_DOMAIN')
URL = 'https://api.telegram.org'


def escape(text):
    return re.sub(r'([:_~*\[\]()>#+-={}|.!])', r'\\\1', text)


def show_message(chat_id, thread_id, text):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': escape(text), 'parse_mode': 'MarkdownV2'}
    if thread_id:
        data['message_thread_id'] = thread_id

    requests.post(url, json=data)


def send_message(chat_id, text):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': escape(text), 'parse_mode': 'MarkdownV2'}

    res = requests.post(url, json=data)
    if not res.ok:
        return None
    res = res.json().get('result')
    return res and res.get('message_id')


def edit_message(chat_id, message_id, text):
    url = f'{URL}/bot{TG_BOT_TOKEN}/editMessageText'
    data = {'chat_id': chat_id, 'text': escape(text), 'message_id': message_id, 'parse_mode': 'MarkdownV2'}
    res = requests.post(url, data=data)
    return res.ok or 'are exactly the same' in res.json().get('description', '')


def delete_message(chat_id, message_id):
    url = f'{URL}/bot{TG_BOT_TOKEN}/deleteMessage'
    data = {'chat_id': chat_id, 'message_id': message_id}
    return requests.post(url, data=data).ok


def create_poll(chat_id, thread_id, poll):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendPoll'
    data = {
        'chat_id': chat_id,
        'question': poll['question'],
        'options': json.dumps(poll['options'], ensure_ascii=False),
        'is_anonymous': poll.get('is_anonymous', False),
        'allows_multiple_answers': poll.get('allows_multiple_answers', False)
    }
    if thread_id:
        data['message_thread_id'] = thread_id

    res = requests.post(url, json=data)
    if not res.ok:
        print(f'err: {res.text}')
        return None

    return res.json().get('result')


def is_admin(user_id, group_id):
    url = f'{URL}/bot{TG_BOT_TOKEN}/getChatMember'
    res = requests.post(url, json={
        'chat_id': group_id,
        'user_id': user_id
    })
    if not res.ok:
        print(f'err: {res.text}')
        return None
    status = res.json()['result'].get('status')
    return status in ('creator', 'administrator')


def get_chat(id):
    url = f'{URL}/bot{TG_BOT_TOKEN}/getChat'
    res = requests.post(url, json={'chat_id': id})
    if not res.ok:
        print(f'err: {res.text}')
        return None
    return res.json()['result']


def set_webhook():
    url = f'{URL}/bot{TG_BOT_TOKEN}/setWebhook'
    res = requests.post(url, json={'url': f'{API_GATEWAY_DOMAIN}/fshtb-function'})
    print(res.json())


def delete_webhook():
    url = f'{URL}/bot{TG_BOT_TOKEN}/deleteWebhook'
    requests.post(url)
