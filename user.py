SERVER = False

if SERVER:
    import mysql.connector as connector
else:
    import sqlite3 as connector


class User:
    def __init__(self, login, password, keyword, aliases=None):
        self.login = login
        self.password = password
        self.keyword = keyword
        self.aliases = aliases or {}

    def get_aliases(self, db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        res = {}

        cur.execute(f"SELECT * FROM aliases WHERE Login_for_who = '{self.login}'")
        for row in cur.fetchall():
            res[row[0]] = row[2]

        return res

    def get_dialoged(self, db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        res = []

        cur.execute(f"SELECT * FROM messages WHERE Login_to = '{self.login}' OR Login_from = '{self.login}'")
        for i in cur.fetchall():
            usr = User.find_by_login(i[0], db_data), User.find_by_login(i[1], db_data)
            for u in usr:
                if u is not None and u not in res:
                    res.append(u)

        return [i for i in res if i is not None and i != self]

    @staticmethod
    def create_table(db_data):
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                Login NVARCHAR(100) PRIMARY KEY NOT NULL UNIQUE,
                Password NVARCHAR(100) NOT NULL,
                Keyword NVARCHAR(100) NOT NULL
            )
        ''')
        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                Login_from NVARCHAR(100) NOT NULL,
                Login_to NVARCHAR(100) NOT NULL,
                Message NVARCHAR(100000),
                Time REAL NOT NULL UNIQUE,
                FOREIGN KEY (Login_from) REFERENCES users (Login) ON DELETE CASCADE,
                FOREIGN KEY (Login_to) REFERENCES users (Login) ON DELETE CASCADE 
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS aliases (
                Login_aliased NVARCHAR(100) NOT NULL,
                Login_for_who NVARCHAR(100) NOT NULL,
                Alias NVARCHAR(100) NOT NULL,
                FOREIGN KEY (Login_aliased) REFERENCES users(Login),
                FOREIGN KEY (Login_for_who) REFERENCES users(Login)
            )
        ''')

        db_conn.commit()

    def write_to_db(self, db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()
        if User.find_by_login(self.login, db_data) is None:
            cur.execute(
                f"insert into users values ('{self.login}', '{self.password}', '{self.keyword}')"
            )
        else:
            cur.execute(
                f"update users "
                f"set Password = '{self.password}', Keyword='{self.keyword}' "
                f"where Login = '{self.login}'"
            )
        db_conn.commit()

    @staticmethod
    def get_list(db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()
        cur.execute('SELECT * FROM users')
        res = []
        for u in cur.fetchall():
            res.append(User(*u))
        return res

    @staticmethod
    def find_by_login(login: str, db_data):
        User.create_table(db_data)
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
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()
        cur.execute(f"DELETE FROM users WHERE Login = '{self.login}'")
        db_conn.commit()

    def __repr__(self):
        return f'User({self.login}, {self.password}, {self.keyword!r})'

    def __eq__(self, other):
        return self.login == other.login

    def __ne__(self, other):
        return not self == other
