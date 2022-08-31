import jinja2

import time

from user import User
from base_unit import BaseUnit


class Message(BaseUnit):
    @staticmethod
    def get_list():
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()
        cur.execute("SELECT * FROM messages")
        return [Message(*i) for i in cur.fetchall()]

    def get_html(self, for_: User):
        res = ''
        if self.from_.login != 'SYSTEM':
            sender = self.from_.login
            if sender == for_.login:
                sender = 'Вы'
            res += f'<span class="source">{sender}</span>'

        answered = Message.find_by_time(self.answer_to)
        if answered is not None:
            res += f'<div class="answered">{answered.get_html(for_)}</div>'

        if self.from_.login == 'SYSTEM':
            res += f'''<p class="text">{self.text.replace('""', '"')}</p>'''
        else:
            res += jinja2.Template('<p class="text">{{ text | escape }}</p>').render(text=self.text.replace('""', '"'))

        if self.from_.login != 'SYSTEM':
            def pretty(n: int):
                return f'{"0" if n // 10 == 0 else ""}{n}'
            t = time.localtime(self.time)
            res += f'<span class="date">{pretty(t[2])}.{pretty(t[1])}.{pretty(t[0])}, {pretty(t[3])}:{pretty(t[4])}:{pretty(t[5])}</span>'
        return res

    @staticmethod
    def find_by_time(time_: float):
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()
        cur.execute(f"SELECT * FROM messages WHERE Time = {time_!r}")
        res = None
        for i in cur.fetchall():
            res = Message(User.find_by_login(i[0]), *i[1:])
        return res

    def __repr__(self):
        return f'Message({self.from_}, {self.text!r}, {self.time}, {self.chat_id})'

    def __eq__(self, other):
        return self.time == other.time

    def __init__(self, from_, text, time_, chat_id, answer_to=0):
        self.from_ = from_
        self.text = text
        self.time = time_
        self.chat_id = chat_id
        self.answer_to = answer_to

    @staticmethod
    def send_system_message(text, chat_id):
        system_user = User.find_by_login('SYSTEM')
        if system_user is None:
            return False
        msg = Message(
            system_user,
            text,
            time.time(),
            chat_id,
            0
        )
        msg.write_to_db()

    def write_to_db(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f'''
                SELECT * FROM messages WHERE Time = {self.time!r}
        ''')

        if cur.fetchall():
            cur.execute(f'''
                UPDATE messages SET
                Login_from = '{self.from_.login.replace("'", "''").replace('"', '""')}',
                Message = '{self.text.replace("'", "''").replace('"', '""')}',
                Chat_id = {self.chat_id},
                Answer_to = {self.answer_to!r},
                WHERE Time = {self.time!r}
            ''')
        else:
            cur.execute(
                f"""INSERT INTO messages VALUES (
                    '{self.from_.login.replace("'", "''").replace('"', '""')}',
                    '{self.text.replace("'", "''").replace('"', '""')}',
                    {self.time!r},
                    {self.chat_id},
                    {self.answer_to!r}
                )"""
            )
        db_conn.commit()

    @staticmethod
    def get_messages_from_chat(chat_id):
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f"SELECT * FROM messages WHERE Chat_id = {chat_id}")

        res = []

        for i in cur.fetchall():
            res.append(Message(User.find_by_login(i[0]), i[1], i[2], i[3], i[4]))

        return res
