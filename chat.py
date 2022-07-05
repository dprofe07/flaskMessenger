from base_unit import BaseUnit, generate_rnd_password


class Chat(BaseUnit):
    def __init__(self, id_, name, members, password_for_commands, token=None):
        self.id = id_
        self.members = members
        self.name = name
        self.password_for_commands = password_for_commands
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

    @staticmethod
    def get_list(db_data):
        db_conn = Chat.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute('SELECT * FROM chats')
        res = []
        for i in cur.fetchall():
            res.append(Chat(*i))
        return res

    def change_token(self, db_data):
        self.token = generate_rnd_password(30)
        self.write_to_db(db_data)

    def remove_from_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM chats WHERE Id = {self.id}')
        cur.execute(f'DELETE FROM chat_members WHERE ChatId = {self.id}')
        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')

        db_conn.commit()

    def __repr__(self):
        return f'Chat({self.id}, {self.name!r}, {self.members!r}, {self.password_for_commands!r}, {self.token!r})'

    def write_to_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        if len(self.members) == 0:
            return self.remove_from_db(db_data)

        cur.execute(f'SELECT * FROM chats WHERE Id = {self.id}')

        if cur.fetchall():
            cur.execute(f'''
                UPDATE chats SET
                Name = {self.name!r},
                Password_for_commands = {self.password_for_commands!r},
                Token = {self.token!r}
                WHERE Id = {self.id}
            ''')
        else:
            cur.execute(f'''
                INSERT INTO chats 
                (Name, Password_for_commands, Token)
                VALUES 
                ({self.name!r}, {self.password_for_commands!r}, {self.token!r})
            ''')
            cur.execute('SELECT MAX(Id) FROM chats')
            self.id = cur.fetchall()[0][0]

        cur.execute(f'DELETE FROM chat_members WHERE ChatId = {self.id}')

        for i in self.members:
            cur.execute(f'''
                INSERT INTO chat_members VALUES (
                    {self.id},
                    {i!r}
                )
            ''')

        db_conn.commit()

    @staticmethod
    def from_id(id_, db_data):
        try:
            db_conn = Chat.connect_to_db(db_data)
            cur = db_conn.cursor()

            cur.execute(f'''
                SELECT * FROM chats WHERE Id = {id_}
            ''')

            ch_name, ch_pass, ch_token = cur.fetchall()[0][1:]

            cur.execute(f'''
                SELECT * FROM chat_members WHERE ChatId = {id_}
            ''')

            ch_members = [i[1] for i in cur.fetchall()]

            return Chat(id_, ch_name, ch_members, ch_pass, ch_token)
        except BaseException as e:
            print(e.args)
            return None

    def clear_messages(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')

        db_conn.commit()
