from index import handler
from utils import get_triggers

if __name__ == '__main__':
    # handler({'body': open('body.json').read()})

    print(
        get_triggers('''
        создавай 19 пт напоминай 8 сб
        создавай 20 напоминай 10
        ''')
    )
