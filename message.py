import time

from user import User
from base_unit import BaseUnit


class Message(BaseUnit):
    @staticmethod
    def get_list(db_data):
        db_conn = Message.connect_to_db(db_data)
        cur = db_conn.cursor()
        cur.execute("SELECT * FROM messages")
        return [Message(*i) for i in cur.fetchall()]

    def __repr__(self):
        return f'Message({self.from_}, {self.to}, {self.text!r}, {self.time}, {self.chat_id})'

    def __eq__(self, other):
        return self.time == other.time

    def __init__(self, from_, text, time, chat_id):
        self.from_ = from_
        self.text = text
        self.time = time
        self.chat_id = chat_id

    @staticmethod
    def send_system_message(text, chat_id, db_data):
        system_user = User.find_by_login('SYSTEM', db_data)
        if system_user is None:
            return False
        msg = Message(
            system_user,
            text,
            time.time(),
            chat_id
        )
        msg.write_to_db(db_data)

    def write_to_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        print(f'''
                SELECT * FROM messages WHERE Login_from = {self.from_.login!r} AND 
                Message = {self.text!r} AND 
                Time = {self.time}
        ''')

        print(f'''
                        SELECT * FROM messages WHERE Login_from = {self.from_.login!r} AND 
                        Message = {self.text!r} AND 
                        Time = {self.time}
                ''')
        cur.execute(f'''
                SELECT * FROM messages WHERE Login_from = {self.from_.login!r} AND 
                Message = {self.text!r} AND 
                Time = {self.time}
        ''')


        if cur.fetchall():
            cur.execute(f'''
                UPDATE messages SET
                Login_from = {self.from_.login!r},
                Message = {self.text!r},
                Chat_id = {self.chat_id}
                WHERE Time = {self.time}
            ''')
        else:
            cur.execute(
                f"""INSERT INTO messages VALUES (
                    {self.from_.login!r},
                    {self.text!r},
                    {self.time},
                    {self.chat_id}
                )"""
            )
        db_conn.commit()

    @staticmethod
    def get_messages_from_chat(chat_id, db_data):
        db_conn = Message.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute(f"SELECT * FROM messages WHERE Chat_id = {chat_id}")

        res = []

        for i in cur.fetchall():
            res.append(Message(User.find_by_login(i[0], db_data), i[1], i[2], i[3]))

        return res
