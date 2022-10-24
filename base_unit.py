import sqlite3
from random import choice


def generate_rnd_password(length: int) -> str:
    return ''.join(
        choice('QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm0123456789@!$%^*')
        for _ in range(length)
    )


class BaseUnit:
    db_data = {}

    @staticmethod
    def create_tables():
        db_conn = sqlite3.connect(**BaseUnit.db_data)
        cur = db_conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                Login NVARCHAR(100) PRIMARY KEY NOT NULL,
                Password NVARCHAR(100) NOT NULL,
                Keyword NVARCHAR(100) NOT NULL,
                Token NVARCHAR(100) NOT NULL UNIQUE
            )
        ''')

        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS chats (
                Id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Name NVARCHAR(100) NOT NULL,
                Password_for_commands NVARCHAR(100) NOT NULL,
                Token NVARCHAR(100) NOT NULL UNIQUE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_members (
                ChatId INTEGER NOT NULL,
                UserLogin NVARCHAR(100) NOT NULL,
                FOREIGN KEY (ChatId) REFERENCES chats (Id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (UserLogin) REFERENCES users (Login) ON DELETE CASCADE ON UPDATE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                Login_from NVARCHAR(100) NOT NULL,
                Message NVARCHAR(100000),
                Time REAL NOT NULL UNIQUE PRIMARY KEY,
                Chat_id INTEGER NOT NULL,
                Answer_to REAL NULL,
                FOREIGN KEY (Answer_to) REFERENCES messages (Time),
                FOREIGN KEY (Login_from) REFERENCES users (Login) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (Chat_id) REFERENCES chats (Id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS aliases (
                Login_aliased NVARCHAR(100) NOT NULL,
                Login_for_who NVARCHAR(100) NOT NULL,
                Alias NVARCHAR(100) NOT NULL,
                FOREIGN KEY (Login_aliased) REFERENCES users(Login) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (Login_for_who) REFERENCES users(Login) ON UPDATE CASCADE ON DELETE CASCADE 
            )
        ''')

        db_conn.commit()

    @staticmethod
    def connect_to_db():
        BaseUnit.create_tables()
        db_conn = sqlite3.connect(**BaseUnit.db_data)
        return db_conn

    def write_to_db(self):
        raise NotImplementedError()

    @staticmethod
    def get_list():
        raise NotImplementedError()

    def __repr__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        raise NotImplementedError()

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return True
