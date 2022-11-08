import time

from user import User
from chat import Chat
from message import Message

from flask import request


class BaseFunctions:
    @staticmethod
    def create_chat(creator, name, members, password):
        curr_chat = Chat(-1, name, [creator.login] + members, password)
        curr_chat.write_to_db()
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
    def remove_account(user):
        user.remove_from_db()

    @staticmethod
    def remove_chat(chat):
        chat.remove_from_db()

    @staticmethod
    def change_password(user, new_password, send_message=True):
        user.password = new_password
        user.write_to_db()
        system_user = User.find_by_login('SYSTEM')
        if system_user is not None and send_message and user.login != 'SYSTEM':
            sys_messages = None
            for i in user.get_chats():
                if 'SYSTEM' in i.members:
                    sys_messages = i
            if sys_messages is not None:
                message = Message(
                    system_user,
                    f'Вы сменили пароль. Новый пароль - "{user.password}"',
                    time.time(), sys_messages.id
                )
                message.write_to_db()

    @staticmethod
    def sign_up(user):
        user.write_to_db()

        system_user = User.find_by_login('SYSTEM')
        if system_user is not None and user.login != 'SYSTEM':
            messages = [
                'Добро пожаловать в мессенджер',
                'Это - аккаунт системы, поэтому сообщения выглядят так. ',
                'Такие сообщения - системные',
                'Эти сообщения сгенерированы автоматически',
                'Для того, чтобы написать человеку, нужно создать чат с ним(кнопка "+" на главной странице)',
                'Каждый раз, когда вы будете менять пароль, сюда будет приходить сообщение, чтобы вы его не забыли',
                f'Ваши учётные данные: Логин - "{user.login}", пароль - "{user.password}",'
                f' ключевое слово - "{user.keyword}"'
            ]
            chat_with_system = Chat(-1, 'DIALOG_BETWEEN/SYSTEM;' + user.login, ['SYSTEM', user.login], 'password')
            chat_with_system.write_to_db()
            for i, m in enumerate(messages):
                mess = Message(system_user, m, time.time(), chat_with_system.id)
                mess.write_to_db()
                if i == 2:
                    Message(User('other', '', ''), 'Так выглядят входящие сообщения', time.time(),
                            chat_with_system.id)
                    Message(User(user.login, '', ''), 'А так - отправленные', time.time(), chat_with_system.id)

    @staticmethod
    def execute_message_command(text, curr_chat, curr_user, message_callback=lambda i: None):
        try:
            command = text[2:].split(';')
            if command[0] == 'add-user':
                password = command[1]
                login = command[2]
                message_callback(
                    Message(
                        curr_user,
                        f'!!{command[0]};<HIDDEN>;{login}',
                        time.time(),
                        curr_chat.id
                    ).write_to_db()
                )
                usr = User.find_by_login(login)
                if password != curr_chat.password_for_commands:
                    message_callback(
                        Message.send_system_message(
                            f'Неверный пароль',
                            curr_chat.id
                        )
                    )
                elif usr is None:
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь не найден',
                            curr_chat.id
                        )
                    )
                elif usr.login in curr_chat.members:
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь уже добавлен',
                            curr_chat.id
                        )
                    )
                else:
                    curr_chat.members.append(usr.login)
                    curr_chat.write_to_db()
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь {curr_user.login} добавил пользователя {login}',
                            curr_chat.id
                        )
                    )

            elif command[0] == 'remove-user':
                password = command[1]
                login = command[2]
                message_callback(
                    Message(
                        curr_user,
                        f'!!{command[0]};<HIDDEN>;{login}',
                        time.time(),
                        curr_chat.id
                    ).write_to_db()
                )
                usr = User.find_by_login(login)

                if password != curr_chat.password_for_commands:
                    message_callback(
                        Message.send_system_message(
                            f'Неверный пароль',
                            curr_chat.id
                        )
                    )
                elif usr is None:
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь {login} не найден',
                            curr_chat.id
                        )
                    )
                elif usr.login not in curr_chat.members:
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь не состоит в чате',
                            curr_chat.id
                        )
                    )
                else:
                    curr_chat.members.remove(login)
                    curr_chat.write_to_db()
                    message_callback(
                        Message.send_system_message(
                            f'Пользователь {usr.login} удалён из чата',
                            curr_chat.id
                        )
                    )

            elif command[0] == 'leave':
                message_callback(Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db()
                                 )
                Message.send_system_message(
                    f'Пользователь {curr_user.login} покинул чат',
                    curr_chat.id
                )
                curr_chat.members.remove(curr_user.login)
                curr_chat.write_to_db()
                return {'flash': ('Вы покинули чат', 'success'), 'redirect': '/'}

            elif command[0] == 'send-system-message':
                password = command[1]
                sys_user = User.find_by_login('SYSTEM')
                if sys_user is None:
                    message_callback(Message(
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

            elif command[0] == 'remove-chat':
                password = command[1]

                if password != curr_chat.password_for_commands:
                    message_callback(Message(
                        curr_user,
                        text,
                        time.time(),
                        curr_chat.id
                    ).write_to_db())
                    message_callback(Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id
                    ))
                else:
                    message_callback(Message(
                        curr_user,
                        f'!!{command[0]};<HIDDEN>',
                        time.time(),
                        curr_chat.id
                    ).write_to_db())
                    message_callback(Message.send_system_message(
                        f'Чат будет удалён',
                        curr_chat.id
                    ))
                    curr_chat.remove_from_db()
                    return {'flash': ('Чат успешно удалён', 'success'), 'redirect': '/'}

            elif command[0] == 'clear-chat':
                password = command[1]
                message_callback(Message(
                    curr_user,
                    f'!!{command[0]};<HIDDEN>',
                    time.time(),
                    curr_chat.id
                ).write_to_db())
                if password != curr_chat.password_for_commands:
                    message_callback(Message.send_system_message(
                        f'',
                        curr_chat.id
                    ))
                else:
                    curr_chat.clear_messages()
                    message_callback(Message.send_system_message(
                        f'Чат очищен пользователем {curr_user.login}',
                        curr_chat.id
                    ))

            elif command[0] == 'change-chat-password':
                password = command[1]
                new_password = command[2]
                message_callback(Message(
                    curr_user,
                    f'!!{command[0]};{password};<HIDDEN>',
                    time.time(),
                    curr_chat.id
                ).write_to_db())
                if password != curr_chat.password_for_commands:
                    message_callback(Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id
                    ))
                else:
                    curr_chat.password_for_commands = new_password
                    curr_chat.write_to_db()
                    message_callback(Message.send_system_message(
                        f'Пароль чата изменён',
                        curr_chat.id
                    ))
                    return {'flash': (f'Пароль чата изменён на "{new_password}"', 'success')}

            elif command[0] == 'reset-chat-password':
                password = command[1]
                new_password = command[2]
                sys_user = User.find_by_login('SYSTEM')
                message_callback(Message(
                    curr_user,
                    f'!!{command[0]};password;<HIDDEN>',
                    time.time(),
                    curr_chat.id
                ).write_to_db())
                if sys_user is None:
                    message_callback(Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id
                    ))
                else:
                    if password != sys_user.password:
                        message_callback(Message.send_system_message(
                            f'Пароль неверен',
                            curr_chat.id
                        ))
                    else:
                        curr_chat.password_for_commands = new_password
                        curr_chat.write_to_db()
                        message_callback(Message.send_system_message(
                            f'Пароль чата сброшен',
                            curr_chat.id
                        ))
                        return {'flash': (f'Пароль чата изменён на "{new_password}"', 'success')}

            elif command[0] == 'call-sys-user':
                sys_user = User.find_by_login('SYSTEM')
                message_callback(Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db())
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

            elif command[0] == 'chat-members':
                message_callback(Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db())

                message_callback(Message.send_system_message(
                    f'В чат входят пользователи: {"; ".join(curr_chat.members)}',
                    curr_chat.id
                ))

            elif command[0] == 'do-sql-request':
                return {'NEED': 'sql-request', 'command': command}

            elif command[0] == 'make-invite-code':
                password = command[1]
                message_callback(Message(
                    curr_user,
                    f'!!{command[0]};<HIDDEN>',
                    time.time(),
                    curr_chat.id
                ).write_to_db())
                if password != curr_chat.password_for_commands:
                    message_callback(Message.send_system_message(
                        'Неверный пароль',
                        curr_chat.id
                    ))
                else:
                    import urllib.parse
                    code = curr_chat.token
                    message_callback(Message.send_system_message(
                        f'Сгенерирован код-приглашение: <b><a href="/join-chat?code={urllib.parse.quote_plus(code)}">{code}</a></b><br/><br/>'
                        f'Чтобы сделать код недействительным используйте команду !!reset-invite-code',
                        curr_chat.id
                    ))

            elif command[0] == 'reset-invite-code':
                password = command[1]
                message_callback(Message(
                    curr_user,
                    f'!!{command[0]};<HIDDEN>',
                    time.time(),
                    curr_chat.id
                ).write_to_db())
                if password != curr_chat.password_for_commands:
                    message_callback(Message.send_system_message(
                        'Неверный пароль',
                        curr_chat.id
                    ))
                else:
                    curr_chat.change_token()
                    message_callback(Message.send_system_message(
                        'Предыдущие коды приглашения больше недействительны',
                        curr_chat.id
                    ))

            else:
                message_callback(Message.send_system_message(
                    'Команда не найдена',
                    curr_chat.id
                ))

        except IndexError:
            message_callback(Message(
                curr_user, text, time.time(), curr_chat.id
            ).write_to_db())
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
