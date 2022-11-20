import sqlite3
from random import choice


def generate_rnd_password(length: int) -> str:
    return ''.join(
        choice('QWERTYUIOPASDFGHJKLZXCVBNMqwertyuiopasdfghjklzxcvbnm0123456789@!$%^*')
        for _ in range(length)
    )


class BaseUnit:
    database = 'users.db'

    @staticmethod
    def create_tables():
        db_conn = sqlite3.connect(BaseUnit.database)
        cur = db_conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                Id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Login NVARCHAR(100) NOT NULL UNIQUE,
                Password NVARCHAR(100) NOT NULL,
                Keyword NVARCHAR(100) NOT NULL,
                Token NVARCHAR(100) NOT NULL UNIQUE
            )
        ''')

        cur.execute(f'''
            CREATE TABLE IF NOT EXISTS chats (
                Id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Name NVARCHAR(100) NOT NULL,
                Token NVARCHAR(100) NOT NULL UNIQUE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_members (
                ChatId INTEGER NOT NULL,
                UserId INTEGER NOT NULL,
                FOREIGN KEY (ChatId) REFERENCES chats (Id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (UserId) REFERENCES users (Id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS chat_admins (
                ChatId INTEGER NOT NULL,
                AdminId INTEGER NOT NULL,
                FOREIGN KEY (ChatId) REFERENCES chats (Id) ON DELETE CASCADE,
                FOREIGN KEY (AdminId) REFERENCES users (Id) ON DELETE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS messages (
                Id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                SenderId INTEGER NOT NULL,
                Message NVARCHAR(100000),
                Time REAL NOT NULL UNIQUE,
                Chat_id INTEGER NOT NULL,
                Answer_to INTEGER NULL,
                FOREIGN KEY (Answer_to) REFERENCES messages (Id),
                FOREIGN KEY (SenderId) REFERENCES users (Id) ON DELETE CASCADE ON UPDATE CASCADE,
                FOREIGN KEY (Chat_id) REFERENCES chats (Id) ON DELETE CASCADE ON UPDATE CASCADE
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS aliases (
                Id_aliased INTEGER NOT NULL,
                Id_for_who INTEGER NOT NULL,
                Alias NVARCHAR(100) NOT NULL,
                FOREIGN KEY (Id_aliased) REFERENCES users(Id) ON UPDATE CASCADE ON DELETE CASCADE,
                FOREIGN KEY (Id_for_who) REFERENCES users(Id) ON UPDATE CASCADE ON DELETE CASCADE 
            )
        ''')

        db_conn.commit()

    @staticmethod
    def connect_to_db():
        BaseUnit.create_tables()
        db_conn = sqlite3.connect(BaseUnit.database)
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
