from index import handler
from utils import get_triggers


def test_get_triggers():
    print(
        get_triggers('''
            создавай 19 пт напоминай 8 сб
            создавай 20 напоминай 10
            ''')
    )


if __name__ == '__main__':
    handler({'body': open('body.json').read()})
