from user import connector, User


class Message:
    def __init__(self, from_, to, text, time=None):
        self.from_ = from_
        self.to = to
        self.text = text
        self.time = time

    def write_to_db(self, db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        cur.execute(
                f"SELECT * FROM messages WHERE Login_from = '{self.from_.login}' AND "
                f"Login_to = '{self.to.login}' AND "
                f"Message = '{self.text}' AND "
                f"Time = {self.time}"
        )

        if cur.fetchall():
            cur.execute(
                f"UPDATE messages SET"
                f"Login_from = '{self.from_.login}',"
                f"Login_to = '{self.to.login}',"
                f"Message = '{self.text}',"
                f"Time = {self.time}"
            )
        else:
            cur.execute(
                f"""INSERT INTO messages VALUES (
                    '{self.from_.login}',
                    '{self.to.login}',
                    '{self.text}',
                    {self.time}
                )"""
            )
        db_conn.commit()

    @staticmethod
    def get_messages_between(from_, to, db_data):
        User.create_table(db_data)
        db_conn = connector.connect(**db_data)
        cur = db_conn.cursor()

        cur.execute(f"SELECT * FROM messages WHERE Login_from = '{from_}' AND Login_to = '{to}'")

        user_from = User.find_by_login(from_, db_data)
        user_to = User.find_by_login(to, db_data)

        res = []

        for i in cur.fetchall():
            res.append(Message(user_from, user_to, i[2], i[3]))

        return res
