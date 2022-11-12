import time

from chat import Chat
from message import Message
from user import User


class BaseFunctions:
    @staticmethod
    def create_chat(creator, name, members):
        curr_chat = Chat(-1, name, [creator.login] + members)
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
                    -1,
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
                mess = Message(-1, system_user, m, time.time(), chat_with_system.id)
                mess.write_to_db()
                if i == 2:
                    Message(-1, User('other', '', ''), 'Так выглядят входящие сообщения', time.time(),
                            chat_with_system.id)
                    Message(-1, User(user.login, '', ''), 'А так - отправленные', time.time(), chat_with_system.id)

    @staticmethod
    def execute_message_command(text, curr_chat, curr_user, message_callback=lambda i: None):
        if not text.startswith('!!send-system-message') and not text.startswith('!!do-sql-request') and not text.startswith('!!answer-to'):
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

            if command[0] == 'add-user':
                login = command[1]
                usr = User.find_by_login(login)

                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
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
                login = command[1]
                usr = User.find_by_login(login)

                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
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

            elif command[0] == 'remove-chat':
                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
                else:
                    message_callback(Message.send_system_message(
                        f'Чат будет удалён',
                        curr_chat.id
                    ))
                    curr_chat.remove_from_db()
                    return {'flash': ('Чат успешно удалён', 'success'), 'redirect': '/'}

            elif command[0] == 'clear-chat':
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

            elif command[0] == 'call-sys-user':
                sys_user = User.find_by_login('SYSTEM')

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

            elif command[0] == 'make-invite-code':
                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
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
                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
                else:
                    curr_chat.change_token()
                    message_callback(Message.send_system_message(
                        'Предыдущие коды приглашения больше недействительны',
                        curr_chat.id
                    ))

            elif command[0] == 'make-admin':
                login_who = command[1]
                user = User.find_by_login(login_who)

                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
                elif login_who not in curr_chat.members or user is None:
                    message_callback(Message.send_system_message(
                        f'Пользователь {login_who} не является членом чата',
                        curr_chat.id
                    ))
                elif user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        f'Пользователь {login_who} уже администратор',
                        curr_chat.id
                    ))
                else:
                    message_callback(Message.send_system_message(
                        f'Пользователь {curr_user.login} назначил администратором пользователя {login_who}',
                        curr_chat.id
                    ))
                    user.become_admin(curr_chat.id)

            elif command[0] == 'remove-admin':
                login_who = command[1]
                user = User.find_by_login(login_who)

                if not curr_user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        'Нужны права администратора',
                        curr_chat.id
                    ))
                elif login_who not in curr_chat.members or user is None:
                    message_callback(Message.send_system_message(
                        f'Пользователь {login_who} не является членом чата',
                        curr_chat.id
                    ))
                elif not user.is_admin(curr_chat.id):
                    message_callback(Message.send_system_message(
                        f'Пользователь {login_who} и так не администратор',
                        curr_chat.id
                    ))
                else:
                    message_callback(Message.send_system_message(
                        f'Пользователь {curr_user.login} удалил из администраторов пользователя {login_who}',
                        curr_chat.id
                    ))
                    user.stop_being_admin(curr_chat.id)

            elif command[0] == 'admins' or command[0] == 'chat-admins':
                message_callback(Message.send_system_message(
                    f'Администарторы чата: {"; ".join(curr_chat.get_admins())}',
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
