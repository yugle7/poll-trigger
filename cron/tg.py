import json
import os

import requests

import dotenv

dotenv.load_dotenv()

TG_BOT_TOKEN = os.getenv('TG_BOT_TOKEN')
URL = 'https://api.telegram.org'


def send_message(chat_id, text):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendMessage'
    data = {'chat_id': chat_id, 'text': text, 'parse_mode': 'MarkdownV2'}

    res = requests.post(url, json=data)
    if not res.ok:
        return None
    res = res.json().get('result')
    return res and res.get('message_id')


def create_poll(chat_id, poll):
    url = f'{URL}/bot{TG_BOT_TOKEN}/sendPoll'
    res = requests.post(url, json={
        'chat_id': chat_id,
        'question': poll['question'],
        'options': json.dumps(poll['options'], ensure_ascii=False),
        'is_anonymous': poll.get('is_anonymous', False),
        'allows_multiple_answers': poll.get('allows_multiple_answers', False)
    })
    if not res.ok:
        print(f'err: {res.text}')
        return None

    return res.json().get('result')
