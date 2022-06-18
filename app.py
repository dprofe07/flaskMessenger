import time

import prettytable
from flask import Flask, render_template, request, redirect, flash, make_response

from base_unit import SERVER, connector
from message import Message
from user import User
from chat import Chat


app = Flask(__name__)


if SERVER:
    db_data = {
        'host': 'messenger.mysql.pythonanywhere-services.com',
        'user': 'messenger',
        'password': '7845126Qq',
        'database': 'messenger$messenger',
    }
else:
    db_data = {
        'database': 'static/users_db.db'
    }

app.config['SECRET_KEY'] = 'fdgdfgdfggf786hfg6hfg6h7f'


@app.route('/', methods=['GET', 'POST'])
def index():
    user = User.find_by_login(request.cookies.get('user_login'), db_data)
    chats = []
    if user is not None:
        user.aliases = user.get_aliases(db_data)
        chats = user.get_chats(db_data)
    return render_template('index.html', user=user, hide_home_link=True, chats=chats)


@app.route('/logout')
def logout():
    resp = redirect('/')
    User.remove_from_cookies(resp)
    return resp


@app.route('/remove_account')
def remove_account():
    return render_template('remove_account.html')


@app.route('/remove_account_confirmed')
def remove_account_confirmed():
    user = User.get_from_cookies(request, db_data)
    resp = redirect('/', 302)
    if user is not None:
        user.remove_from_cookies(resp)
        user.remove_from_db(db_data)
    return resp


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'GET':
        return render_template('change_password.html')
    else:
        old_password = request.form['old_password']
        password = request.form['password']
        password2 = request.form['password2']
        user = User.get_from_cookies(request, db_data)
        if user.password != old_password:
            flash('Старый пароль не верен', 'error')
            return render_template(
                'change_password.html',
                old_password=old_password, password=password, password2=password2
            )
        if password != password2:
            flash('Пароли не совпадают', 'error')
            return render_template(
                'change_password.html',
                old_password=old_password,
                password=password
            )

        user.password = password
        user.write_to_db(db_data)
        system_user = User.find_by_login('SYSTEM', db_data)
        if system_user is not None:
            message = Message(system_user, user, f'Вы сменили пароль. Новый пароль - "{user.password}"', time.time())
            message.write_to_db(db_data)
        flash('Пароль успешно изменён', 'success')
        return render_template(
            'change_password.html'
        )


@app.route('/password_recovery', methods=['GET', 'POST'])
def password_recovery():
    if request.method == 'GET':
        return render_template('password_recovery.html')
    else:
        login = request.form['login']
        keyword = request.form['keyword']

        user = User.find_by_login(login, db_data)
        if user is None:
            flash(f'Пользователь с логином "{login}" не найден', 'error')
            return render_template('password_recovery.html', login=login, keyword=keyword)
        if user.keyword != keyword:
            flash(f'Неверное ключевое слово', 'error')
            return render_template('password_recovery.html', login=login, keyword=keyword)
        password = user.password
        resp = make_response(render_template('password_recovery.html', login=login, keyword=keyword, password=password))
        user.save_to_cookies(resp)
        return resp


# noinspection PyUnusedLocal
@app.errorhandler(404)
def err404(e):
    return render_template('error.html', error_message='Страница не найдена')


@app.route('/auth', methods=['POST', 'GET'])
def auth():
    if request.cookies.get('user_login') is not None:
        return redirect('/', 302)
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.find_by_login(login, db_data)
        if user is not None:
            if password == user.password:
                flash('Вы успешно вошли', 'success')

                resp = make_response(render_template('auth.html', redirect_timeout=1000, redirect_address='/'))
                User.save_to_cookies(user, resp)

                return resp
            else:
                flash(f'Неверный пароль для пользователя "{login}"', 'error')
                return render_template('auth.html', login=login, password=password)
        else:
            flash(f'Пользователь с именем "{login}" не найден.', 'error')
            return render_template('auth.html', login=login, password=password)
    else:
        return render_template('auth.html')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if request.cookies.get('user_login') is not None:
        return redirect('/', 302)
    if request.method == 'POST':
        login = request.form['login']

        password = request.form['password']
        password2 = request.form['password2']
        keyword = request.form['keyword']
        if ';' in login:
            flash('Нельзя использовать ";" в логине')
            return render_template('singup.html', login=login, password=password, password2=password2)
        elif password != password2:
            flash(f'Пароли не совпадают', 'error')
            return render_template('singup.html', login=login, password=password)
        elif User.find_by_login(login, db_data) is not None:
            flash(f'Пользователь с именем "{login}" уже существует.', 'error')
            return render_template('singup.html', login=login, password=password, password2=password2)
        else:
            user = User(login, password, keyword)
            user.write_to_db(db_data)

            flash('Вы успешно зарегистрированы', 'success')
            system_user = User.find_by_login('SYSTEM', db_data)
            if system_user is not None and user.login != 'SYSTEM':
                messages = [
                    'Добро пожаловать в мессенджер',
                    'Это - аккаунт системы, поэтому сообщения выглядят так. '
                    'Чтобы увидеть образцы других сообщений, создайте диалог',
                    'Такие сообщения - системные',
                    'Эти сообщения сгенерированы автоматически',
                    'Для того, чтобы написать человеку, нужно создать чат с ним(кнопка "+" на главной странице)',
                    'Каждый раз, когда вы будете менять пароль, сюда будет приходить сообщение, чтобы вы его не забыли',
                    f'Ваши учётные данные: Логин - "{user.login}", пароль - "{user.password}",'
                    f' ключевое слово - "{user.keyword}"'
                ]
                chat_with_system = Chat(-1, 'DIALOG_BETWEEN/SYSTEM-' + user.login, ['SYSTEM', user.login], 'password')
                chat_with_system.write_to_db(db_data)
                for m in messages:
                    mess = Message(system_user, m, time.time(), chat_with_system.id)
                    mess.write_to_db(db_data)

            resp = make_response(render_template('singup.html', redirect_timeout=1000, redirect_address='/'))
            User.save_to_cookies(user, resp)
            return resp
    else:
        return render_template('singup.html')


@app.route('/chat/<id_>')
def chat(id_):
    curr_user = User.get_from_cookies(request, db_data)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    curr_chat = Chat.from_id(id_, db_data)
    if curr_chat is None:
        flash('Чат не найден в базе данных', 'error')
        return redirect('/')
    if curr_user.login not in curr_chat.members:
        flash('Вступите в чат, чтобы просмотреть его')
        return redirect('/')
    messages = Message.get_messages_from_chat(curr_chat.id, db_data)

    messages.sort(key=lambda i: i.time)
    return render_template('chat.html', user=curr_user, messages=messages, chat=curr_chat)


# noinspection DuplicatedCode
@app.route('/send-message-to-chat/<chat_id>', methods=['POST'])
def send_message_to(chat_id):
    curr_user = User.get_from_cookies(request, db_data)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    curr_chat = Chat.from_id(chat_id, db_data)
    if curr_chat is None:
        flash('Чат не найден в базе данных', 'error')
        return redirect('/')
    if curr_user.login not in curr_chat.members:
        flash('Чтобы отправлять сообщения, вступите в чат', 'error')
        return redirect('/')
    text = request.form['message']
    if text.startswith('!!'):
        try:
            command = text[2:].split(';')
            if command[0] == 'add-user':
                password = command[1]
                login = command[2]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                usr = User.find_by_login(login, db_data)
                if password != curr_chat.password_for_commands:
                    Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id, db_data
                    )
                elif usr is None:
                    Message.send_system_message(
                        f'Пользователь не найден',
                        curr_chat.id, db_data
                    )
                elif usr.login in curr_chat.members:
                    Message.send_system_message(
                        f'Пользователь уже добавлен',
                        curr_chat.id, db_data
                    )
                else:
                    curr_chat.members.append(usr.login)
                    curr_chat.write_to_db(db_data)
                    Message.send_system_message(
                        f'Пользователь {curr_user.login} добавил пользователя {login}',
                        curr_chat.id, db_data
                    )
            elif command[0] == 'remove-user':
                password = command[1]
                login = command[2]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                usr = User.find_by_login(login, db_data)

                if password != curr_chat.password_for_commands:
                    Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id, db_data
                    )
                elif usr is None:
                    Message.send_system_message(
                        f'Пользователь {login} не найден',
                        curr_chat.id, db_data
                    )
                elif usr.login not in curr_chat.members:
                    Message.send_system_message(
                        f'Пользователь не состоит в чате',
                        curr_chat.id, db_data
                    )
                else:
                    curr_chat.members.remove(login)
                    curr_chat.write_to_db(db_data)
                    Message.send_system_message(
                        f'Пользователь {usr.login} удалён из чата',
                        curr_chat.id, db_data
                    )
            elif command[0] == 'leave':
                Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                Message.send_system_message(
                    f'Пользователь {curr_user.login} покинул чат',
                    curr_chat.id, db_data
                )
                curr_chat.members.remove(curr_user.login)
                curr_chat.write_to_db(db_data)

                flash('Вы покинули чат', 'success')
                return redirect('/')
            elif command[0] == 'send-system-message':
                password = command[1]
                sys_user = User.find_by_login('SYSTEM', db_data)
                if sys_user is None:
                    Message(
                        curr_user,
                        text.replace(password, '<HIDDEN>'),
                        time.time(),
                        curr_chat.id
                    ).write_to_db(db_data)
                    Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id, db_data
                    )
                else:
                    if password != sys_user.password:
                        Message(
                            curr_user,
                            text.replace(password, '<HIDDEN>'),
                            time.time(),
                            curr_chat.id
                        ).write_to_db(db_data)
                        Message.send_system_message(
                            f'Неверный пароль',
                            curr_chat.id, db_data
                        )
                    else:
                        Message.send_system_message(
                            ' '.join(command[2:]),
                            curr_chat.id, db_data
                        )
            elif command[0] == 'remove-chat':
                password = command[1]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                if password != curr_chat.password_for_commands:
                    Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id, db_data
                    )
                else:
                    Message.send_system_message(
                        f'Чат будет удалён',
                        curr_chat.id, db_data
                    )
                    curr_chat.remove_from_db(db_data)
                    flash('Чат успешно удалён', 'success')
                    return redirect('/')
            elif command[0] == 'clear-chat':
                password = command[1]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                if password != curr_chat.password_for_commands:
                    Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id, db_data
                    )
                else:
                    curr_chat.clear_messages(db_data)
                    Message.send_system_message(
                        f'Чат успешно очищен пользователем {curr_user.login}',
                        curr_chat.id, db_data
                    )
            elif command[0] == 'change-chat-password':
                password = command[1]
                new_password = command[2]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>').replace(new_password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                if password != curr_chat.password_for_commands:
                    Message.send_system_message(
                        f'Неверный пароль',
                        curr_chat.id, db_data
                    )
                else:
                    curr_chat.password_for_commands = new_password
                    curr_chat.write_to_db(db_data)
                    flash(f'Пароль чата изменён на "{new_password}"')
                    Message.send_system_message(
                        f'Пароль чата изменён',
                        curr_chat.id, db_data
                    )
            elif command[0] == 'reset-chat-password':
                password = command[1]
                new_password = command[2]
                sys_user = User.find_by_login('SYSTEM', db_data)
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>').replace(new_password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                if sys_user is None:
                    Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id, db_data
                    )
                else:
                    if password != sys_user.password:
                        Message.send_system_message(
                            f'Пароль неверен',
                            curr_chat.id, db_data
                        )
                    else:
                        curr_chat.password_for_commands = new_password
                        curr_chat.write_to_db(db_data)
                        flash(f'Пароль чата изменён на "{new_password}"')
                        Message.send_system_message(
                            f'Пароль чата сброшен',
                            curr_chat.id, db_data
                        )
            elif command[0] == 'call-sys-user':
                sys_user = User.find_by_login('SYSTEM', db_data)
                Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)
                if sys_user is None:
                    Message.send_system_message(
                        'Системный пользователь не создан',
                        curr_chat.id, db_data
                    )
                else:
                    curr_chat.members.append('SYSTEM')
                    curr_chat.write_to_db(db_data)
                    Message.send_system_message(
                        f'Пользователь {curr_user.login} добавил системного пользователя в чат',
                        curr_chat.id, db_data
                    )
            elif command[0] == 'chat-members':
                Message(
                    curr_user,
                    text,
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)

                Message.send_system_message(
                    f'В чат входят пользователи: {"; ".join(curr_chat.members)}',
                    curr_chat.id, db_data
                )
            elif command[0] == 'do-sql-request':
                password = command[1]
                Message(
                    curr_user,
                    text.replace(password, '<HIDDEN>'),
                    time.time(),
                    curr_chat.id
                ).write_to_db(db_data)

                req = command[2]
                try:
                    db_conn = connector.connect(**db_data)
                    cur = db_conn.cursor()
                    cur.execute(req)

                    tbl = prettytable.from_db_cursor(cur)
                    Message.send_system_message(
                        str(tbl),
                        curr_chat.id, db_data
                    )

                except BaseException as e:
                    Message.send_system_message(
                        f'Произошла ошибка: {e.args}',
                        curr_chat.id, db_data
                    )
            else:
                Message.send_system_message(
                    'Команда не найдена',
                    curr_chat.id,
                    db_data
                )

        except IndexError:
            Message(
                curr_user, text, time.time(), curr_chat.id
            ).write_to_db(db_data)
            Message.send_system_message(
                f'Ошибка в аргументах команды',
                curr_chat.id, db_data
            )
    else:
        if text.startswith('`!!'):
            text = text[1:]
        new_message = Message(curr_user, text, time.time(), curr_chat.id)
        new_message.write_to_db(db_data)
    return redirect(f'/chat/{chat_id}')


@app.route('/new-chat', methods=['POST'])
def new_chat():
    curr_user = User.get_from_cookies(request, db_data)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    chat_name = request.form['chat-name']
    users = [i for i in request.form['users'].split(';') if User.find_by_login(i, db_data)]
    password = request.form['password']

    curr_chat = Chat(-1, chat_name, [curr_user.login] + users, password)
    curr_chat.write_to_db(db_data)
    Message.send_system_message(
        f'Пользователь {curr_user.login} создал чат "{curr_chat.name}"',
        curr_chat.id, db_data
    )
    for usr_login in users:
        Message.send_system_message(
            f'Пользователь {curr_user.login} пригласил пользователя {usr_login}',
            curr_chat.id, db_data
        )

    return redirect(f'/chat/{curr_chat.id}')


@app.route('/new-dialog', methods=['POST'])
def new_dialog():
    curr_user = User.get_from_cookies(request, db_data)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    login = request.form['login']
    if User.find_by_login(login, db_data) is None:
        flash('Пользователь не найден', 'error')
        return redirect('/')

    curr_chat = Chat(-1, f'DIALOG_BETWEEN/{login}-{curr_user.login}', [curr_user.login, login], '')
    curr_chat.write_to_db(db_data)
    Message.send_system_message(
        f'Пользователь {curr_user.login} создал диалог с пользователем {login}',
        curr_chat.id, db_data
    )

    return redirect(f'/chat/{curr_chat.id}')


@app.route('/get-messages-div/<chat_id>')
def get_messages_div(chat_id):
    curr_user = User.get_from_cookies(request, db_data)
    curr_chat = Chat.from_id(chat_id, db_data)
    if curr_chat is None:
        return (f'''
            <div class="messages-container">
                <div class="message-system">
                    Ошибка! Не удалось найти чат.
                </div>
            </div>
        ''')
    messages = Message.get_messages_from_chat(chat_id, db_data)

    messages.sort(key=lambda i: i.time)

    a = render_template('messages-div.html', user=curr_user, messages=messages)

    return a


@app.route('/get-dialogs-div')
def get_dialogs_div():
    user = User.get_from_cookies(request, db_data)
    chats = user.get_chats(db_data)
    return render_template('dialogs-div.html', chats=chats, user=user)


if __name__ == '__main__':
    app.run('192.168.1.12', port=5000, debug=not SERVER)
