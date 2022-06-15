SERVER = False

if SERVER:
    import mysql.connector as connector
else:
    import sqlite3 as connector


class BaseUnit:
    @staticmethod
    def create_tables(db_data):
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        cur.execute('''
            CREATE TABLE IF NOT EXISTS users (
                Login NVARCHAR(100) PRIMARY KEY NOT NULL,
                Password NVARCHAR(100) NOT NULL,
                Keyword NVARCHAR(100) NOT NULL
            )
        ''')

        cur.execute('''
            CREATE TABLE IF NOT EXISTS chats (
                Id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
                Name NVARCHAR(100) NOT NULL,
                Password_for_commands NVARCHAR(100) NOT NULL
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
                Time REAL NOT NULL UNIQUE,
                Chat_id INTEGER NOT NULL,
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
    def connect_to_db(db_data):
        BaseUnit.create_tables(db_data)
        db_conn = connector.connect(**db_data)
        return db_conn

    def write_to_db(self, db_data):
        raise NotImplementedError()

    @staticmethod
    def get_list(db_data):
        raise NotImplementedError()

    def __repr__(self):
        raise NotImplementedError()

    def __eq__(self, other):
        raise NotImplementedError()

    def __ne__(self, other):
        return not self == other

    def __bool__(self):
        return True
