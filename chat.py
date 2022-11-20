from base_unit import BaseUnit, generate_rnd_password


class Chat(BaseUnit):
    def __init__(self, id_, name, members, token=None):
        self.id = id_
        self.members = members
        self.members_logins = members
        self.name = name
        self.token = token or generate_rnd_password(30)
        self.show_name = None

    @property
    def show_name(self):
        if self.__show_name is None:
            return self.name
        return self.__show_name

    @show_name.setter
    def show_name(self, new_val):
        self.__show_name = new_val

    def __eq__(self, other):
        return self.id == other.id

    @property
    def last_message_time(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f"SELECT Time FROM messages WHERE Chat_id = {self.id}")
        times = [i[0] for i in cur.fetchall()]
        return max(times)

    @staticmethod
    def get_list():
        db_conn = Chat.connect_to_db()
        cur = db_conn.cursor()

        cur.execute('SELECT * FROM chats')
        res = []
        for i in cur.fetchall():
            res.append(Chat(*i))
        return res

    def change_token(self):
        self.token = generate_rnd_password(30)
        self.write_to_db()

    def remove_from_db(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM chats WHERE Id = {self.id}')
        cur.execute(f'DELETE FROM chat_members WHERE ChatId = {self.id}')
        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')
        cur.execute(f'DELETE FROM chat_admins WHERE ChatId = {self.id}')

        db_conn.commit()

    def __repr__(self):
        return f'''Chat({self.id}, {self.name!r}, {self.members!r}, {self.token!r})'''

    def write_to_db(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        if len(self.members) == 0:
            return self.remove_from_db()

        cur.execute(f'SELECT * FROM chats WHERE Id = {self.id}')

        if cur.fetchall():
            cur.execute(f'''
                UPDATE chats SET
                Name = '{self.name.replace("'", "''")}',
                Token = {self.token!r}
                WHERE Id = {self.id}
            ''')
        else:
            cur.execute(f'''
                INSERT INTO chats 
                (Name, Token)
                VALUES 
                (
                    '{self.name.replace("'", "''")}', 
                    {self.token!r}
                )
            ''')
            cur.execute('SELECT MAX(Id) FROM chats')
            self.id = cur.fetchone()[0]

        cur.execute(f'DELETE FROM chat_members WHERE ChatId = {self.id}')

        for i in self.members:
            cur.execute(f'''
                INSERT INTO chat_members VALUES (
                    {self.id},
                    {i}
                )
            ''')

        db_conn.commit()

    @staticmethod
    def from_id(id_: str or None):
        if id_ is None:
            return None
        try:
            db_conn = Chat.connect_to_db()
            cur = db_conn.cursor()

            cur.execute(f'''
                SELECT * FROM chats WHERE Id = {id_}
            ''')

            res = cur.fetchall()

            if not res:
                return None

            ch_name, ch_token = res[0][1:]

            cur.execute(f'''
                SELECT * FROM chat_members WHERE ChatId = {id_}
            ''')

            ch_members = [i[1] for i in cur.fetchall()]
            chat = Chat(id_, ch_name, ch_members, ch_token)
            if not ch_members:
                chat.remove_from_db()
                chat = None

            return chat
        except TypeError as e:
            return None

    @staticmethod
    def from_token(token):
        if token is None:
            return None

        try:
            db_conn = Chat.connect_to_db()
            cur = db_conn.cursor()

            cur.execute(f'''
                SELECT * FROM chats WHERE Token = {token!r}
            ''')

            id_, ch_name, ch_token = cur.fetchall()[0]

            cur.execute(f'''
                SELECT * FROM chat_members WHERE ChatId = {id_}
            ''')

            ch_members = [i[1] for i in cur.fetchall()]
            chat = Chat(id_, ch_name, ch_members, ch_token)
            if not ch_members:
                chat.remove_from_db()
                chat = None

            return chat
        except BaseException as e:
            print('B', e.args)
            return None

    def clear_messages(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')

        db_conn.commit()

    def get_admins(self):
        db_conn = self.connect_to_db()
        cur = db_conn.cursor()

        cur.execute(f'SELECT AdminId FROM chat_admins WHERE ChatId = {self.id}')

        res = [i[0] for i in cur.fetchall()]

        return res
