import time

from chat import Chat
from message import Message
from user import User
from runtime_storage import storage

class BaseFunctions:
    @staticmethod
    def create_chat(creator, name, members):
        curr_chat = Chat(-1, name, [creator.id] + members)
        curr_chat.write_to_db()
        creator.become_admin(curr_chat.id)
        Message.send_system_message(
            f'Пользователь {creator.login} создал чат "{curr_chat.name}"',
            curr_chat.id
        )
        for usr_login in members:
            Message.send_system_message(
                f'Пользователь {creator.login} пригласил пользователя {usr_login}',
                curr_chat.id
            )
        return curr_chat

    @staticmethod
    def change_password(user, new_password, send_message=True):
        user.password = new_password
        user.write_to_db()
        system_user = User.find_by_login_('SYSTEM')
        if system_user is not None and send_message and user.login != 'SYSTEM':
            sys_messages = None
            for i in user.get_chats():
                if 'SYSTEM' in i.members:
                    sys_messages = i
            if sys_messages is not None:
                message = Message(
                    -1,
                    system_user,
                    f'Вы сменили пароль. Новый пароль - "{user.password}"',
                    time.time(), sys_messages.id
                )
                message.write_to_db()

    @staticmethod
    def sign_up(user):
        user.write_to_db()

        system_user = User.find_by_login_('SYSTEM')
        if system_user is not None and user.login != 'SYSTEM':
            messages = [
                'Добро пожаловать в мессенджер',
                'Это - аккаунт системы, поэтому сообщения выглядят так. ',
                'Такие сообщения - системные',
                'Эти сообщения сгенерированы автоматически',
                'Для того, чтобы написать человеку, нужно создать чат с ним (кнопка "+" на главной странице)',
                'Каждый раз, когда вы будете менять пароль, сюда будет приходить сообщение, чтобы вы его не забыли',
                f'Ваши учётные данные: Логин - "{user.login}", пароль - "{user.password}",'
                f' ключевое слово - "{user.keyword}"'
            ]
            chat_with_system = Chat(-1, 'DIALOG_BETWEEN/SYSTEM;' + user.login, [system_user.id, user.id])
            chat_with_system.write_to_db()
            for i, m in enumerate(messages):
                Message(
                    -1,
                    system_user,
                    m,
                    time.time(),
                    chat_with_system.id
                ).write_to_db()

                if i == 2:
                    Message(
                        -1,
                        User(
                            -1,
                            'Другой пользователь',
                            '', ''
                        ),
                        'Так выглядят входящие сообщения',
                        time.time(),
                        chat_with_system.id
                    ).write_to_db()

                    Message(
                        -1,
                        user,
                        'А так - отправленные',
                        time.time(),
                        chat_with_system.id
                    ).write_to_db()

    @staticmethod
    def execute_message_command(text, curr_chat, curr_user, message_callback=lambda i: None):
        if (
                not text.startswith('!!send-system-message') and
                not text.startswith('!!do-sql-request') and
                not text.startswith('!!answer-to')
        ):
            message_callback(
                Message(
                    -1,
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db()
            )

        try:
            command = text[2:].split(';')

            if command[0] == 'send-system-message':
                password = command[1]
                sys_user = User.find_by_login_('SYSTEM')
                if sys_user is None:
                    message_callback(Message(
                        -1,
                        curr_user,
                        f'!!{command[0]};<HIDDEN>;{command[2]}',
                        time.time(),
                        curr_chat.id
                    ).write_to_db())
                    message_callback(Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id
                    ))
                else:
                    if password != sys_user.password:
                        message_callback(Message(
                            -1,
                            curr_user,
                            f'!!{command[0]};<HIDDEN>;{command[2]}',
                            time.time(),
                            curr_chat.id
                        ).write_to_db())
                        message_callback(Message.send_system_message(
                            f'Неверный пароль',
                            curr_chat.id
                        ))
                    else:
                        message_callback(Message.send_system_message(
                            ' '.join(command[2:]),
                            curr_chat.id
                        ))

            elif command[0] == 'call-sys-user':
                sys_user = User.find_by_login_('SYSTEM')

                if sys_user is None:
                    message_callback(Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id
                    ))
                else:
                    curr_chat.members.append('SYSTEM')
                    curr_chat.write_to_db()
                    message_callback(Message.send_system_message(
                        f'Пользователь {curr_user.login} добавил системного пользователя в чат',
                        curr_chat.id
                    ))

            elif command[0] == 'chat-members' or command[0] == 'members':
                message_callback(Message.send_system_message(
                    f'В чат входят пользователи: {"; ".join(curr_chat.members)}',
                    curr_chat.id
                ))

            elif command[0] == 'do-sql-request':
                return {'NEED': 'sql-request', 'command': command}

            elif command[0] == 'admins' or command[0] == 'chat-admins':
                message_callback(Message.send_system_message(
                    f'Администарторы чата: {"; ".join(User.find_by_id(i).login for i in curr_chat.get_admins())}',
                    curr_chat.id
                ))
            elif command[0] == 'answer-to':
                try:
                    msg_id = int(command[1])
                except ValueError:
                    message_callback(
                        Message(
                            -1,
                            curr_user,
                            text,
                            time.time(),
                            curr_chat.id
                        ).write_to_db()
                    )
                    message_callback(Message.send_system_message(
                        'Некорректный ID сообщения',
                        curr_chat.id
                    ))
                else:
                    text = ';'.join(command[2:])
                    answered_msg = Message.find_by_id(msg_id)
                    if answered_msg is None:
                        message_callback(
                            Message(
                                -1,
                                curr_user,
                                text,
                                time.time(),
                                curr_chat.id
                            ).write_to_db()
                        )
                        message_callback(Message.send_system_message(
                            'Неверный ID сообщения',
                            curr_chat.id
                        ))
                    elif answered_msg.chat_id != curr_chat.id:
                        message_callback(
                            Message(
                                -1,
                                curr_user,
                                text,
                                time.time(),
                                curr_chat.id
                            ).write_to_db()
                        )
                        message_callback(Message.send_system_message(
                            'Сообщение не из этого чата',
                            curr_chat.id
                        ))
                    else:
                        message_callback(
                            Message(
                                -1,
                                curr_user,
                                text,
                                time.time(),
                                curr_chat.id,
                                msg_id
                            ).write_to_db()
                        )

            else:
                message_callback(Message.send_system_message(
                    'Команда не найдена',
                    curr_chat.id
                ))

        except IndexError:
            message_callback(Message.send_system_message(
                f'Ошибка в аргументах команды',
                curr_chat.id
            ))
        return {}

    @staticmethod
    def any_is_none(*args):
        return any(map(lambda i: i is None, args))

    @staticmethod
    def which_is_none(values_to_check: list, values_to_return: list):
        if len(values_to_check) != len(values_to_return):
            return None

        for i in range(len(values_to_check)):
            if values_to_check[i] is None:
                return values_to_return[i]

    @staticmethod
    def make_invite_code(curr_user, curr_chat, message_callback=lambda msg: None):
        if not curr_user.is_admin(curr_chat.id):
            message_callback(Message.send_system_message(
                'Нужны права администратора',
                curr_chat.id
            ))
        else:
            import urllib.parse
            code = curr_chat.token
            message_callback(Message.send_system_message(
                f'Сгенерирован код-приглашение: '
                f'<b><a href="{"/messenger" if storage.is_server else ""}/join-chat?code={urllib.parse.quote_plus(code)}">{code}</a></b><br/><br/>'
                f'Чтобы сделать код недействительным используйте команду !!reset-invite-code',
                curr_chat.id
            ))

    @staticmethod
    def clear_chat(curr_user, curr_chat, message_callback=lambda msg: None):
        if not curr_user.is_admin(curr_chat.id):
            message_callback(Message.send_system_message(
                'Нужны права администратора',
                curr_chat.id
            ))
        else:
            curr_chat.clear_messages()
            message_callback(Message.send_system_message(
                f'Чат очищен пользователем {curr_user.login}',
                curr_chat.id
            ))

