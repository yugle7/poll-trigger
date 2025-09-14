from cityhash import CityHash64
from datetime import datetime, timedelta
import re

from const import *


def get_id(a, b):
    return CityHash64(str(a) + ' ' + str(b).lower().strip())


def what(cron, dh):
    question = cron['poll']['question']
    stopped = not cron['create']
    answers = [f'{question}` {"остановлен" if stopped else "запущен"}`']

    if cron['create']:
        create = datetime.fromtimestamp(cron['create'] + 3600 * dh)
        month = MONTH[create.month - 1]
        answers.append(f'— создам` {create.hour}:00 {create.day} {month}`')

    trigger = cron.get('trigger')
    if trigger:
        if trigger['create']:
            answers.append(f'— создаю` {when(trigger["create"], dh)}`')
        if trigger['notify']:
            answers.append(f'— напоминаю` {when(trigger["notify"], dh)}`')

    return '\n'.join(answers)


def when(triggers, dh):
    answers = []
    for t in triggers:
        t = shift(t, dh)
        hour = t['hour']
        weekday = t.get('weekday')
        if weekday is None:
            day = 'каждый день'
        else:
            day = WEEKDAY[weekday]
        answers.append(f'{day} {hour:02}:00')
    return ', '.join(answers)


def next(trigger):
    now = datetime.now()

    t = now.replace(hour=trigger['hour'], minute=0, second=0, microsecond=0)
    weekday = trigger.get('weekday')
    if weekday is not None:
        days = (weekday - now.weekday()) % 7
        if days == 0:
            if t.hour <= now.hour:
                t += timedelta(days=7)
        else:
            t += timedelta(days=days)
    else:
        if t.hour <= now.hour:
            t += timedelta(days=1)

    return int(t.timestamp())


def shift(trigger, dh):
    w = trigger.get('weekday')
    h = trigger['hour'] + dh
    return {'hour': h % 24} if w is None else {'weekday': (w + h // 24) % 7, 'hour': h % 24}


class Token:
    def __init__(self, k, v=None):
        self.k = k
        self.v = v


def stem(word):
    word = word.removesuffix('те')
    for end in ACTION_ENDS:
        if word.endswith(end):
            return word[:-len(end)]
    return word


def get_command(text):
    change = False
    for w in text.split():
        a = ACTIONS.get(stem(w))
        if a in ('stop', 'resume', 'delete', 'show'):
            return a
        if a in ('create', 'notify'):
            if any(w.isdigit() for w in text):
                change = True
            else:
                return a
    return 'change' if change else None


def get_pattern(tokens):
    t = ''.join(t.k for t in tokens)
    if 'w' in t:
        ps = ['a *w+ *h', 'a *h *w+', 'w+ *h *a', 'h *w+ *a', 'w *+a *h', 'h *a *w+']
    else:
        ps = ['a *h', 'h *a']

    ns = [len(re.findall(p, t)) for p in ps]
    k = t.count('a')
    for n, p in zip(ns, ps):
        if n == k:
            return p
    return ''


def get_words(text):
    return re.sub(r':\d+', ' ', text).replace(MENTION, '\n').replace(',', '\n').replace('.', ' ').replace('\n', ' | ').split()


def get_changes(text):
    words = get_words(text)
    tokens = get_tokens(words)

    if not tokens:
        return None

    changes = []
    for t in tokens:
        if t.k == 'A':
            changes.append(('not ' + t.v, None, None))

    p = get_pattern(tokens)
    if not p:
        return None

    while True:
        t = ''.join(t.k for t in tokens)
        m = re.search(p, t)
        if not m:
            return changes
        i, j = m.span()

        ws = []
        a = ''
        h = 0
        for t in tokens[i: j]:
            if t.k == 'h':
                h = t.v
                t.k = ' '
            elif t.k == 'w':
                t.k = ' '
                ws.append(t.v)
            elif t.k == 'a':
                a = t.v
        for w in ws or [None]:
            changes.append((a, h, w))


def get_tokens(words):
    tokens = []
    for i in range(len(words)):
        t = get_hour(words, i) or get_action(words, i) or get_weekday(words, i) or get_void(words, i)
        if t is None:
            tokens.append(Token(' '))
        elif t.k != 'v':
            tokens.append(t)

    V = {t.v for t in tokens if t.k == 'A'}
    v = {t.v for t in tokens if t.k == 'a'}
    if V & v:
        return None

    return tokens


def get_split(words, i):
    return Token('|') if words[i] == '|' else None


def get_void(words, i):
    return Token('v') if words[i] in VOIDS else None


def get_action(words, i):
    w = stem(words[i])
    if w not in ACTIONS:
        return None
    action = ACTIONS[w]
    if i > 0 and words[i - 1] in NOT:
        return Token('A', action)
    return Token('a', action)


def get_hour(words, i):
    w = words[i]
    if w.isdigit():
        hour = int(w)
        i += 1
        if i < len(words) and words[i] == 'час':
            words[i] = ''
    elif w in TENS:
        hour = TENS[w]
        i += 1
        if i < len(words):
            if words[i] in DIGITS:
                hour += DIGITS[words[i]]
                words[i] = ''
    elif w in HOURS:
        hour = HOURS[words[i]]
    else:
        return None
    if 0 <= hour < 24:
        return Token('h', hour)
    return None


def get_weekday(words, i):
    w = words[i]
    if w in WEEKDAY:
        weekday = WEEKDAY.index(w)
    else:
        for end in WEEKDAY_ENDS:
            w = w.removesuffix(end)
        if w in WEEKDAYS:
            weekday = WEEKDAYS.index(w)
        else:
            return None
    return Token('w', weekday)


def clear_text(text):
    text = re.sub(r':\d+', ' ', text).lower().replace('ё', 'е')
    return re.sub(r'[^а-я0-9]', ' ', text).strip()
