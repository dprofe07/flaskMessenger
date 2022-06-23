from base_unit import BaseUnit
from chat import Chat

from random import choice


def generate_rnd_password(length: int) -> str:
    return ''.join(
        choice('QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm0123456789@!$%^*')
        for _ in range(length)
    )


class User(BaseUnit):
    def __init__(self, login, password, keyword, token=None, aliases=None):
        self.login = login
        self.password = password
        self.keyword = keyword
        self.token = token or generate_rnd_password(30)
        self.aliases = aliases or {}

    def get_aliases(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        res = {}

        cur.execute(f"SELECT * FROM aliases WHERE Login_for_who = {self.login!r}")
        for row in cur.fetchall():
            res[row[0]] = row[2]

        return res

    def get_chats(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        res = []

        cur.execute(f"SELECT * FROM chat_members WHERE UserLogin = {self.login!r}")
        for i in cur.fetchall():
            if i[0] not in res:
                res.append(i[0])

        res = [[0, i] for i in res]

        for chat in res:
            cur.execute(f"SELECT * FROM messages WHERE Chat_id = {chat[1]}")
            for message in cur.fetchall():
                chat[0] = max(chat[0], message[2])

        res.sort(key=lambda i: i[0])
        res.reverse()

        return [Chat.from_id(i[1], db_data) for i in res]

    def write_to_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        if User.find_by_login(self.login, db_data) is None:
            cur.execute(
                f"insert into users values ({self.login!r}, {self.password!r}, {self.keyword!r}, {self.token!r})"
            )
        else:
            cur.execute(
                f"update users "
                f"set Password = {self.password!r}, Keyword={self.keyword!r}, Token={self.token!r} "
                f"where Login = {self.login!r}"
            )
        db_conn.commit()

    @staticmethod
    def get_list(db_data):
        db_conn = User.connect_to_db(db_data)
        cur = db_conn.cursor()
        cur.execute('SELECT * FROM users')
        res = []
        for u in cur.fetchall():
            res.append(User(*u))
        return res

    @staticmethod
    def find_by_token(token: str, db_data):
        db_conn = User.connect_to_db(db_data)
        cur = db_conn.cursor()
        if not isinstance(token, str):
            return None

        cur.execute(f'SELECT * FROM users WHERE Token = {token!r}')
        res = cur.fetchall()
        if len(res) == 0:
            return None
        return User(*res[0])

    @staticmethod
    def find_by_login(login: str, db_data):
        db_conn = User.connect_to_db(db_data)
        cur = db_conn.cursor()
        if not isinstance(login, str):
            return None
        cur.execute(f'SELECT * FROM users WHERE Login = {login!r}')
        res = cur.fetchall()
        if len(res) == 0:
            return None
        return User(*res[0])

    def save_to_cookies(self, resp):
        resp.set_cookie('user_token', self.token, 60 * 60 * 24 * 365 * 1000)
        # on 1000 years

    @staticmethod
    def remove_from_cookies(resp):
        resp.set_cookie('user_token', '', 0)
        # on 0 seconds (expire and remove)

    @staticmethod
    def get_from_cookies(request, db_data):
        return User.find_by_token(request.cookies.get('user_token'), db_data)

    def remove_from_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()
        cur.execute(f"DELETE FROM users WHERE Login = {self.login!r}")
        cur.execute(f"DELETE FROM chat_members WHERE UserLogin = {self.login!r}")
        db_conn.commit()

    def __repr__(self):
        return f'User({self.login!r}, {self.password!r}, {self.keyword!r}, {self.token!r})'

    def __eq__(self, other):
        return self.login == other.login

    def __ne__(self, other):
        return not self == other

    @staticmethod
    def generate_new_token():
        return generate_rnd_password(30)
