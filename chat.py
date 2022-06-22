from base_unit import BaseUnit


class Chat(BaseUnit):
    def __init__(self, id_, name, members, password_for_commands):
        self.id = id_
        self.members = members
        self.name = name
        self.password_for_commands = password_for_commands

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

    def remove_from_db(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM chats WHERE Id = {self.id}')
        cur.execute(f'DELETE FROM chat_members WHERE ChatId = {self.id}')
        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')

        db_conn.commit()

    def __repr__(self):
        return f'Chat({self.id}, {self.name!r}, {self.members!r})'

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
                Password_for_commands = {self.password_for_commands!r}
                WHERE Id = {self.id}
            ''')
        else:
            cur.execute(f'''
                INSERT INTO chats 
                (Name, Password_for_commands)
                VALUES 
                ({self.name!r}, {self.password_for_commands!r})
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

            ch_name, ch_pass = cur.fetchall()[0][1:]

            cur.execute(f'''
                SELECT * FROM chat_members WHERE ChatId = {id_}
            ''')

            ch_members = [i[1] for i in cur.fetchall()]

            return Chat(id_, ch_name, ch_members, ch_pass)
        except:
            return None

    def clear_messages(self, db_data):
        db_conn = self.connect_to_db(db_data)
        cur = db_conn.cursor()

        cur.execute(f'DELETE FROM messages WHERE Chat_id = {self.id}')

        db_conn.commit()
