from base_unit import BaseUnit
from chat import Chat


class User(BaseUnit):
    def __init__(self, login, password, keyword, aliases=None):
        self.login = login
        self.password = password
        self.keyword = keyword
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
            res.append(Chat.from_id(i[0], db_data))

        return res

    def write_to_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        if User.find_by_login(self.login, db_data) is None:
            cur.execute(
                f"insert into users values ({self.login!r}, {self.password!r}, {self.keyword!r})"
            )
        else:
            cur.execute(
                f"update users "
                f"set Password = {self.password!r}, Keyword={self.keyword!r} "
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
    def find_by_login(login: str, db_data):
        for i in User.get_list(db_data):
            if i.login == login:
                return i
        return None

    def save_to_cookies(self, resp):
        resp.set_cookie('user_login', self.login, 60 * 60 * 24 * 365 * 1000)
        # on 1000 years

    @staticmethod
    def remove_from_cookies(resp):
        resp.set_cookie('user_login', '', 0)
        # on 0 seconds (expire and remove)

    @staticmethod
    def get_from_cookies(request, db_data):
        return User.find_by_login(request.cookies.get('user_login'), db_data)

    def remove_from_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()
        cur.execute(f"DELETE FROM users WHERE Login = {self.login!r}")
        db_conn.commit()

    def __repr__(self):
        return f'User({self.login!r}, {self.password!r}, {self.keyword!r})'

    def __eq__(self, other):
        return self.login == other.login

    def __ne__(self, other):
        return not self == other
