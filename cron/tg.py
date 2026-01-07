import json
import os

import requests

import dotenv
import re

dotenv.load_dotenv()

TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
URL = 'https://api.telegram.org'


def escape(text):
    return re.sub(r'([_.])', r'\\\1', text)


def show_message(chat_id, thread_id, text):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': escape(text), 'parse_mode': 'MarkdownV2'}
    if thread_id:
        data['message_thread_id'] = thread_id

    requests.post(url, json=data)


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
