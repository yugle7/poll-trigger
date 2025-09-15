from cityhash import CityHash64
from datetime import datetime, timedelta
import re

from const import *


def get_id(a, b):
    return CityHash64(str(a) + ' ' + str(b).lower().strip())


def what(cron, user):
    question = cron['poll']['question']
    stopped = not cron['create']
    answers = [f'"{question}" {"остановлен" if stopped else "создаётся"}']

    if cron['create']:
        time_zone = timedelta(hours=user['time_zone'])
        create = datetime.fromtimestamp(cron['create']) + time_zone
        month = MONTH[create.month - 1]
        answers.append(f'— создам {create.hour}:00 {create.day} {month}')

    triggers = cron['triggers']
    if triggers['create']:
        answers.append(f'— создаю {when(triggers["create"], user)}')
    if triggers['notify']:
        answers.append(f'— напоминаю {when(triggers["notify"], user)}')

    return '\n'.join(answers)


def when(triggers, user):
    answers = []
    for t in triggers:
        hour = t['hour']

        y = t.get('year')
        m = t.get('month')
        d = t.get('day')

        if 'weekday' in t:
            answer = WEEKDAY[t['weekday']]
        elif y and m and d:
            answer = f'{d} {MONTH[m - 1]} {y}'
        else:
            if d:
                if m:
                    answer = f'ежегодно {d} {MONTH[m - 1]}'
                else:
                    answer = f'ежемесячно {d} числа'
            elif m:
                answer = f'ежедневно весь {MONTH[m - 1]}'
            else:
                answer = f'каждый день'
            if y:
                answer += f'в {y} году'

        hour += int(user['time_zone'] - t['time_zone'])
        answers.append(f'{answer} {hour:02}:00')

    return ', '.join(answers)


def get_next(trigger):
    time_zone = timedelta(hours=trigger['time_zone'])
    now = datetime.now() + time_zone
    t = now.replace(hour=trigger['hour'], minute=0, second=0, microsecond=0)

    y = trigger.get('year')
    m = trigger.get('month')
    d = trigger.get('day')

    if y:
        t = t.replace(year=y, month=1, day=1)
    if m:
        t = t.replace(month=m, day=1)
    if d:
        t = t.replace(day=d)

    if 'weekday' in trigger:
        days = (trigger['weekday'] - t.weekday()) % 7
        if days:
            t += timedelta(days=days)
        elif t <= now:
            t += timedelta(days=7)

    elif t <= now:
        if y and m and d:
            return 0

        if d:
            if m:
                t = t.replace(year=t.year + 1)
            elif t.month == 12:
                t = t.replace(year=t.year + 1, month=1)
            else:
                t = t.replace(month=t.month + 1)
        else:
            t += timedelta(days=1)

    if m and t.month != m:
        return 0

    return int((t - time_zone).timestamp())


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
    action = None
    for w in text.split():
        a = ACTIONS.get(stem(w))
        if a in ('stop', 'resume', 'delete', 'show'):
            return a
        if a in ('create', 'notify'):
            action = a
    return 'change' if any(w.isdigit() for w in text) else action


def get_text(text):
    text = text.lower().replace('ё', 'е').replace(',', ' ').replace(MENTION, '\n')
    text = re.sub(r':\d+', ' час', text)
    text = re.sub(r'[^0-9а-яn\n]', ' ', text)
    text = re.sub(r'(\d\d\d\d) (\d\d?) (\d\d?)', r'\1-\2-\3', text)
    text = re.sub(r'(\d\d?) (\d\d?) (\d\d\d\d)', r'\3-\2-\1', text)
    text = text.replace('полночь', '0 час')
    text = text.replace('полдень', '12 час')
    return text.replace('\n', ' | ')


class A:
    def __init__(self):
        self.a = []
        self.s = []
        self.h = H()

    def add(self, q):
        if isinstance(q, str):
            if self.h:
                self.a.append(self.h)
                self.h = H()

            if self.a:
                self.s.append(self.a)
                self.a = []

            if q in ('create', 'notify'):
                self.s.append(q)
        else:
            self.h.add(q)

    def get(self, v):
        if self.h:
            self.a.append(self.h)

        if self.a:
            self.s.append(self.a)

        a = None
        self.a = []

        t = {k: [] for k in v}

        while self.s:
            s = self.s.pop()
            if isinstance(s, str):
                if self.a:
                    t[s] += self.a
                    a = None
                    self.a = []
                else:
                    a = s
            else:
                if a:
                    for h in s:
                        t[a] += h.get()
                else:
                    for h in s:
                        self.a += h.get()

        return {} if self.a else t


class H:
    def __init__(self):
        self.q = []
        self.s = []
        self.h = None

    def __bool__(self):
        return self.h is not None

    def add(self, q):
        h = 'hour' in q
        if self.h is not None and self.h != h:
            self.s.append(self.q)
            self.q = [q]
        else:
            self.q.append(q)
        self.h = h

    def get(self):
        while self.s:
            s = self.s.pop()
            if not self.q:
                self.q = s
                continue
            for y in s:
                for x in self.q:
                    y.update(x)
                    yield y
            self.q = []
        for q in self.q:
            if 'hour' in q:
                yield q


def get_triggers(text):
    words = text.split()
    tokens = get_tokens(words)

    if not tokens:
        return {}

    a = A()
    k = ''.join(t.k for t in tokens)
    v = {t.v for t in tokens if t.k in 'Aa'}

    for m in re.finditer('a|A|x|w|nmN?|d|nh?', k):
        i, j = m.span()

        if m[0] == 'a':
            a.add(tokens[i].v)
        elif m[0] in 'Ax':
            a.add('')
        elif m[0] in ('n', 'nh'):
            hour = tokens[i].v
            if hour >= 24:
                return {}
            a.add({'hour': hour})
        elif m[0] == 'w':
            a.add({'weekday': tokens[i].v})
        elif m[0] == 'nmN':
            a.add({
                'day': tokens[i].v,
                'month': tokens[i + 1].v,
                'year': tokens[i + 2].v
            })
        elif m[0] == 'nm':
            a.add({
                'day': tokens[i].v,
                'month': tokens[i + 1].v,
            })
        elif m[0] == 'd':
            a.add({
                'day': tokens[i].v[0],
                'month': tokens[i].v[1],
                'year': tokens[i].v[2]
            })

    return a.get(v)


def get_tokens(words):
    tokens = []
    for i in range(len(words)):
        t = get_number(words, i) or get_action(words, i) or get_weekday(words, i) or get_month(words, i) or get_date(words, i) or get_void(words, i) or get_split(words, i)
        if t is None:
            tokens.append(Token(' '))
        elif t.k != 'v':
            tokens.append(t)

    V = {t.v for t in tokens if t.k == 'A'}
    v = {t.v for t in tokens if t.k == 'a'}
    if V & v:
        return None

    return tokens


def get_date(words, i):
    m = re.fullmatch(r'(\d\d\d\d)-(\d\d?)-(\d\d?)', words[i])
    return m and Token('d', (int(m[3]), int(m[2]), int(m[1])))


def get_split(words, i):
    return Token('x') if words[i] == '|' else None


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
    if w.startswith('час') and len(w) <= 4:
        i += 1
        if i < len(words) and words[i] in ('дня', 'вечера'):
            return Token('h', 12)
        return Token('h', 0)
    return None


def get_number(words, i):
    w = words[i]
    if w.isdigit():
        number = int(w)
        i += 1
    elif w in TENS:
        number = TENS[w]
        i += 1
        if i < len(words) and words[i] in DIGITS:
            number += DIGITS[words[i]]
            words[i] = ''
    elif w in TEENS:
        number = TENS[w]
    else:
        return None
    return Token('N' if number > 31 else 'n', number)


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


def get_month(words, i):
    w = words[i]
    if w in MONTH:
        month = MONTH.index(w) + 1
    else:
        if w[-1] in MONTH_ENDS:
            w = w[:-1]
        if w in MONTHS:
            month = MONTHS.index(w) + 1
        else:
            return None
    return Token('m', month)
