import jinja2

import time

from user import User
from base_unit import BaseUnit


class Message(BaseUnit):
    def __init__(self, id_, from_, text, time_, chat_id, answer_to=0):
        if isinstance(from_, str):
            from_ = User(-1, from_, '', '')
        self.id = id_
        self.from_ = from_
        self.text = text
        self.time = time_
        self.chat_id = chat_id
        self.answer_to = answer_to

    @staticmethod
    def get_list():
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()
        cur.execute("SELECT * FROM messages")
        return [Message(*i) for i in cur.fetchall()]

    def get_html(self, for_: User):
        res = '<div class="message-header">'
        any_ = for_ is None
        if self.from_.login != 'SYSTEM':
            sender = self.from_.login
            if not any_ and sender == for_.login:
                sender = 'Вы'
            res += f'<span class="source">{sender}</span>'

        if self.from_.login != 'SYSTEM':
            res += f'<a style="float:right" href="javascript:on_message_click({self.id})">Ответить</a>'
        res += '</div>'
        answered = Message.find_by_id(self.answer_to)
        if answered is not None:
            res += f'<div class="answered">{answered.get_html(for_)}</div>'


        if self.from_.login == 'SYSTEM':
            res += f'''<span class="text">{self.text}</span>'''
        else:
            res += (
                    '<span class="text">' +
                    self.process_message_text(self.text) +
                    '</span>'
            )

        if self.from_.login != 'SYSTEM':
            def pretty(n: int):
                return f'{"0" if n // 10 == 0 else ""}{n}'
            t = time.localtime(self.time)
            res += f'<span class="date">{pretty(t[2])}.{pretty(t[1])}.{pretty(t[0])},' \
                   f' {pretty(t[3])}:{pretty(t[4])}:{pretty(t[5])}</span>'
        res += f'<span style="display: none;" class="message-id">{self.id}</span>'
        return res

    @staticmethod
    def find_by_id(id_):
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()
        cur.execute(f"SELECT * FROM messages WHERE Id = {id_}")
        res = None
        for i in cur.fetchall():
            res = Message(i[0], User.find_by_id(i[1]), i[2], *i[3:])
        return res

    def __repr__(self):
        return f'Message({self.id}, {self.from_}, {self.text!r}, {self.time}, {self.chat_id})'

    def __eq__(self, other):
        return self.time == other.time

    @staticmethod
    def send_system_message(text, chat_id):
        system_user = User.find_by_login_('SYSTEM')
        if system_user is None:
            return False
        msg = Message(
            -1,
            system_user,
            text,
            time.time(),
            chat_id,
            0
        )
        msg.write_to_db()
        return msg

    def write_to_db(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f'''
                SELECT * FROM messages WHERE Id = {self.id}
        ''')

        if cur.fetchall():
            cur.execute(f'''
                UPDATE messages SET
                SenderId = {self.from_.id},
                Message = '{self.text.replace("'", "''")}',
                Chat_id = {self.chat_id},
                Answer_to = {self.answer_to!r},
                WHERE Id = {self.id}
            ''')
        else:
            cur.execute(
                f"""INSERT INTO messages (SenderId, Message, Time, Chat_id, Answer_to) VALUES (
                    {self.from_.id},
                    '{self.text.replace("'", "''")}',
                    {self.time!r},
                    {self.chat_id},
                    {self.answer_to!r}
                )"""
            )

            cur.execute('SELECT MAX(Id) FROM messages')
            self.id = cur.fetchall()[0][0]

        db_conn.commit()
        return self

    @staticmethod
    def get_messages_from_chat(chat_id):
        db_conn = Message.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f"SELECT * FROM messages WHERE Chat_id = {chat_id}")

        res = []

        for i in cur.fetchall():
            user = User.find_by_id(i[1])
            if user is None:
                user = i[1]
            res.append(Message(i[0], user, *i[2:]))

        return res

    @staticmethod
    def process_message_text(text):
        splited = text.split(' ')
        for i in range(len(splited)):
            if splited[i].startswith('lnk:'):
                link = jinja2.runtime.escape(splited[i][4:])
                link = link.lower()\
                    .replace('%2f', '/')\
                    .replace('%3a', ':')\
                    .replace('%26', '&')\
                    .replace('%5c', '\\')\
                    .replace('%23', '#')\
                    .replace('%3f', '?')
                if not link.startswith('http'):
                    link = 'http://' + link
                splited[i] = f'<a target="_blank" href="{link}">{link}</a>'
            elif splited[i].startswith('img:'):
                link = jinja2.runtime.escape(splited[i][4:])
                link = link.lower()\
                    .replace('%2f', '/')\
                    .replace('%3a', ':')\
                    .replace('%26', '&')\
                    .replace('%5c', '\\')\
                    .replace('%23', '#')\
                    .replace('%3f', '?')
                if not link.startswith('http'):
                    link = 'http://' + link
                splited[i] = f'<img src="{link}"/>'
            else:
                splited[i] = jinja2.runtime.escape(splited[i])
        return ' '.join(splited)

