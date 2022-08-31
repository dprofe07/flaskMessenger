import json
import time

import prettytable
from flask import Flask, render_template, request, redirect, flash, make_response, send_file
from flask_socketio import SocketIO, send, join_room

from base_unit import SERVER, BaseUnit
from message import Message
from user import User
from chat import Chat
from base_functions import BaseFunctions
from forms import forms


app = Flask(__name__)
io = SocketIO(app, cors_allowed_origins='*')

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
BaseUnit.db_data = db_data


@io.on('join')
def join(data):
    join_room(data['room'])


def socket_send_message(message, room):
    new_data = {
        'html_sender': message.get_html(message.from_),
        'html_any': message.get_html(None),
        'source': message.from_.login,
    }

    send(new_data, to=room)


@io.on('message')
def handle_message(data):
    user = User.find_by_login(data['source'])

    if user is None:
        return
    curr_chat = Chat.from_id(int(data['room']))
    if curr_chat is None:
        return

    if user.login not in curr_chat.members and user.login != 'SYSTEM':
        return
    text = data['text']

    if text.startswith('!!'):
        res = BaseFunctions.execute_message_command(
            text,
            curr_chat,
            user,
            lambda message: socket_send_message(message, data['room'])
        )

        if 'NEED' in res:
            command = res['command']
            password = command[1]
            msg = Message(
                user,
                text.replace(password, '<HIDDEN>'),
                time.time(),
                curr_chat.id
            ).write_to_db()
            socket_send_message(msg, data['room'])

            sys_user = User.find_by_login('SYSTEM')
            if sys_user is None:
                msg = Message.send_system_message(
                    'Системный пользователь не создан',
                    curr_chat.id
                )
                socket_send_message(msg, data['room'])
            else:
                if password != sys_user.password:
                    msg = Message.send_system_message(
                        'Неверный пароль',
                        curr_chat.id
                    )

                    socket_send_message(msg, data['room'])
                else:
                    req = command[2]
                    try:
                        db_conn = BaseUnit.connect_to_db()
                        cur = db_conn.cursor()
                        cur.execute(req)

                        tbl = prettytable.from_db_cursor(cur)
                        msg = Message.send_system_message(
                            '<code>' + str(tbl).replace('\n', '<br/>').replace(' ', '&nbsp;') + '</code>',
                            curr_chat.id
                        )

                        socket_send_message(msg, data['room'])

                    except BaseException as e:
                        msg = Message.send_system_message(
                            f'Произошла ошибка: {e.args}',
                            curr_chat.id
                        )
                        socket_send_message(msg, data['room'])
    else:
        if text.startswith('`!!'):
            text = text[1:]
        new_message = Message(user, text, time.time(), curr_chat.id)
        new_message.write_to_db()

        socket_send_message(new_message, data['room'])


@app.route('/', methods=['GET', 'POST'])
def index():
    user = User.get_from_cookies(request)
    if user is None:
        return render_template('guest.html',  title='Главная')
    else:
        user.aliases = user.get_aliases()
        chats = user.get_chats()
        return render_template(
            'index.html',
            user=user,
            hide_home_link=True,
            chats=chats,
            title='Главная'
        )


@app.route('/logout')
def logout():
    resp = redirect('/')
    User.remove_from_cookies(resp)
    return resp


@app.route('/remove_account')
def remove_account():
    return render_template('remove_account.html', title='Удалить аккаунт')


@app.route('/remove_account_confirmed')
def remove_account_confirmed():
    user = User.get_from_cookies(request)
    resp = redirect('/')
    if user is not None:
        user.remove_from_cookies(resp)
        BaseFunctions.remove_account(user)
    return resp


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'GET':
        return render_template('change_password.html', title='Смена пароля')
    else:
        old_password = request.form['old_password']
        password = request.form['password']
        password2 = request.form['password2']
        user = User.get_from_cookies(request)
        if user.password != old_password:
            flash('Старый пароль не верен', 'error')
            return render_template(
                'change_password.html',
                old_password=old_password,
                password=password,
                password2=password2,
                title='Смена пароля'
            )
        if password != password2:
            flash('Пароли не совпадают', 'error')
            return render_template(
                'change_password.html',
                old_password=old_password,
                password=password,
                title='Смена пароля'
            )

        BaseFunctions.change_password(user, password)

        flash('Пароль успешно изменён', 'success')
        return render_template(
            'change_password.html',
            title='Смена пароля'
        )


@app.route('/password_recovery', methods=['GET', 'POST'])
def password_recovery():
    if request.method == 'GET':
        return render_template('password_recovery.html', title='Восстановление пароля')
    else:
        login = request.form['login']
        keyword = request.form['keyword']

        user = User.find_by_login(login)
        if user is None:
            flash(f'Пользователь с логином "{login}" не найден', 'error')
            return render_template('password_recovery.html', login=login, keyword=keyword, title='Восстановление пароля')
        if user.keyword != keyword:
            flash(f'Неверное ключевое слово', 'error')
            return render_template('password_recovery.html', login=login, keyword=keyword, title='Восстановление пароля')
        password = user.password
        resp = make_response(
            render_template(
                'password_recovery.html',
                login=login,
                keyword=keyword,
                password=password,
                title='Восстановление пароля'
            )
        )
        user.save_to_cookies(resp)
        return resp


# noinspection PyUnusedLocal
@app.errorhandler(404)
def err404(e):
    return render_template('error.html', msg='Страница не найдена', title='Ошибка')


# noinspection PyUnusedLocal
@app.errorhandler(500)
def err500(e):
    return render_template(
        'error.html',
        msg='Ошибка 500. Скорее всего слабенький бесплатный сервер не справляется с нагрузкой',
        title='Ошибка'
    )


@app.route('/auth', methods=['POST', 'GET'])
def auth():
    if User.get_from_cookies(request) is not None:
        return redirect('/')
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.find_by_login(login)
        if user is not None:
            if password == user.password:
                flash('Вы успешно вошли', 'success')

                resp = make_response(
                    render_template(
                        'form.html',
                        title='Авторизация',
                        form=forms['login'],
                        name='login',
                        redirect_timeout=1000,
                        redirect_address='/'
                    )
                )
                User.save_to_cookies(user, resp)

                return resp
            else:
                flash(f'Неверный пароль для пользователя "{login}"', 'error')
                return render_template(
                    'form.html',
                    title='Авторизация',
                    form=forms['login'](login, password),
                    name='login'
                )
        else:
            flash(f'Пользователь с именем "{login}" не найден.', 'error')
            return render_template(
                'form.html',
                title='Авторизиция',
                form=forms['login'](login, password),
                name='login'
            )
    else:
        return render_template('form.html', form=forms['login'], name='login', title='Авторизация')


@app.route('/signup', methods=['POST', 'GET'])
def signup():
    if User.get_from_cookies(request) is not None:
        return redirect('/')
    if request.method == 'POST':
        login = request.form['login']

        password = request.form['password']
        password2 = request.form['password2']
        keyword = request.form['keyword']
        if ';' in login:
            flash('Нельзя использовать ";" в логине')
            return render_template(
                'form.html',
                title='Регистрация',
                name='register',
                form=forms['register'](login, password, password2, keyword)
            )
        elif password != password2:
            flash(f'Пароли не совпадают', 'error')
            return render_template(
                'form.html',
                title='Регистрация',
                name='register',
                form=forms['register'](login, password, '', keyword)
            )
        elif User.find_by_login(login) is not None:
            flash(f'Пользователь с именем "{login}" уже существует.', 'error')
            return render_template(
                'form.html',
                title='Регистрация',
                name='register',
                form=forms['register'](login, password, password2, keyword)
            )
        else:
            user = User(login, password, keyword)
            BaseFunctions.sign_up(user)

            flash('Вы успешно зарегистрированы', 'success')

            resp = make_response(
                render_template(
                    'form.html',
                    title='Регистрация',
                    name='register',
                    form=forms['register']()
                )
            )
            user.save_to_cookies(resp)
            return resp
    else:
        return render_template(
            'form.html',
            title='Регистрация',
            name='register',
            form=forms['register']
        )


# noinspection DuplicatedCode
@app.route('/chat/<id_>')
def chat(id_):
    curr_user = User.get_from_cookies(request)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    curr_chat = Chat.from_id(id_)
    if curr_chat is None:
        flash('Чат не найден в базе данных', 'error')
        return redirect('/')
    if curr_user.login not in curr_chat.members and curr_user.login != 'SYSTEM':
        flash('Вступите в чат, чтобы просмотреть его', 'error')
        return redirect('/')
    messages = Message.get_messages_from_chat(curr_chat.id)

    messages.sort(key=lambda i: i.time)
    dialog = 'DIALOG_BETWEEN' in curr_chat.name
    if dialog:
        new_name = curr_chat.name.replace('DIALOG_BETWEEN/', '', 1)
        dialoged = new_name.split(';')
        if curr_user.login in dialoged:
            dialoged.remove(curr_user.login)
            other = dialoged[0]
            curr_chat.show_name = f'Диалог с {other}'
        else:
            curr_chat.show_name = f'Диалог между {dialoged[0]} и {dialoged[1]}'
    return render_template(
        'new_chat.html',
        title=curr_chat.show_name if dialog else f'Чат {curr_chat.show_name}',
        user=curr_user,
        messages=messages,
        chat=curr_chat
    )


@app.route('/change-token')
def change_token():
    curr_user = User.get_from_cookies(request)
    if curr_user is None:
        return redirect('/')
    curr_user.token = User.generate_new_token()
    curr_user.write_to_db()
    resp = redirect('/')
    curr_user.save_to_cookies(resp)
    flash('Вы вышли на всех устройствах', 'success')
    return resp


# noinspection DuplicatedCode
@app.route('/send-message-to-chat/<chat_id>', methods=['POST'])
def send_message_to(chat_id):
    curr_user = User.get_from_cookies(request)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    curr_chat = Chat.from_id(chat_id)
    if curr_chat is None:
        flash('Чат не найден в базе данных', 'error')
        return redirect('/')
    if curr_user.login not in curr_chat.members:
        if curr_user.login != 'SYSTEM':
            flash('Чтобы отправлять сообщения, вступите в чат', 'error')
            return redirect('/')
    text = request.form['message']

    if text.startswith('!!'):
        res = BaseFunctions.execute_message_command(text, curr_chat, curr_user)

        if 'NEED' in res:
            command = res['command']
            password = command[1]
            Message(
                curr_user,
                text.replace(password, '<HIDDEN>'),
                time.time(),
                curr_chat.id
            ).write_to_db()
            sys_user = User.find_by_login('SYSTEM')
            if sys_user is None:
                Message.send_system_message(
                    'Системный пользователь не создан',
                    curr_chat.id
                )
            else:
                if password != sys_user.password:
                    Message.send_system_message(
                        'Неверный пароль',
                        curr_chat.id
                    )
                else:
                    req = command[2]
                    try:
                        db_conn = BaseUnit.connect_to_db()
                        cur = db_conn.cursor()
                        cur.execute(req)

                        tbl = prettytable.from_db_cursor(cur)
                        Message.send_system_message(
                            '<code>' + str(tbl).replace('\n', '<br/>').replace(' ', '&nbsp;') + '</code>',
                            curr_chat.id
                        )

                    except BaseException as e:
                        Message.send_system_message(
                            f'Произошла ошибка: {e.args}',
                            curr_chat.id
                        )

        if res.get('flash') is not None:
            flash(*res['flash'])

        if res.get('redirect') is not None:
            return redirect(res['redirect'])
    else:
        if text.startswith('`!!'):
            text = text[1:]
        new_message = Message(curr_user, text, time.time(), curr_chat.id)
        new_message.write_to_db()
    return redirect(f'/chat/{chat_id}')


@app.route('/new-chat', methods=['POST'])
def new_chat():
    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    chat_name = request.form['chat-name']
    if 'DIALOG_BETWEEN' in chat_name:
        flash(f'Недопустимое название чата: "{chat_name}"', 'error')
    users = []
    for i in request.form['users'].split(';'):
        if i not in users and i != curr_user.login:
            if User.find_by_login(i):
                users.append(i)
    password = request.form['password']

    curr_chat = BaseFunctions.create_chat(curr_user, chat_name, users, password)

    return redirect(f'/chat/{curr_chat.id}')


@app.route('/new-dialog', methods=['POST'])
def new_dialog():
    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    login = request.form['login']
    if login == curr_user.login:
        flash('Нельзя создать диалог с самим собой. Используйте чат.', 'error')
        return redirect('/')
    if User.find_by_login(login) is None:
        flash('Пользователь не найден', 'error')
        return redirect('/')

    curr_chat = Chat(-1, f'DIALOG_BETWEEN/{login};{curr_user.login}', [curr_user.login, login], '')
    curr_chat.write_to_db()
    Message.send_system_message(
        f'Пользователь {curr_user.login} создал диалог с пользователем {login}',
        curr_chat.id
    )

    return redirect(f'/chat/{curr_chat.id}')


@app.route('/join-chat')
def invite_to_chat():
    code = request.args.get('code')

    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите на сайт чтобы использовать коды-приглашения', 'error')
        return redirect('/')
    if '&&' not in code:
        flash('Некорректный код-приглашение', 'error')
        return redirect('/')
    id_, code = code.split('&&')
    try:
        id_ = int(id_)
    except ValueError:
        flash('Некорректный код-приглашение', 'error')
        return redirect('/')

    curr_chat = Chat.from_id(id_)
    if curr_chat is None:
        flash('Некорректный код-приглашение', 'error')
        return redirect('/')

    if curr_chat.token != code:
        flash('Неверный код-приглашение', 'error')
        return redirect('/')

    if curr_user.login in curr_chat.members:
        flash('Вы уже состоите в этом чате')
    else:
        curr_chat.members.append(curr_user.login)
        curr_chat.write_to_db()

        Message.send_system_message(
            f'Пользователь {curr_user.login} присоединился к чату по коду-приглашению',
            curr_chat.id
        )
    return redirect(f'/chat/{curr_chat.id}')


@app.route('/download-app')
def download_app():
    return send_file('static/messenger_app.apk', as_attachment=True)


@app.route('/get-messages-div/<chat_id>')
def get_messages_div(chat_id):
    curr_user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)
    if curr_chat is None:
        return (f'''
            <div class="messages-container">
                <div class="message message-system">
                    Ошибка! Не удалось найти чат.
                </div>
            </div>
        ''')
    messages = Message.get_messages_from_chat(chat_id)

    messages.sort(key=lambda i: i.time)

    return render_template('messages-div.html', user=curr_user, messages=messages)


@app.route('/get-dialogs-div')
def get_dialogs_div():
    user = User.get_from_cookies(request)
    chats = user.get_chats()
    return render_template('dialogs-div.html', chats=chats, user=user)


# noinspection PyPep8Naming
class API_CODES:
    SUCCESS = 0
    NOT_A_CHAT_MEMBER = 1
    CHAT_NOT_FOUND = 2
    FORBIDDEN_SYMBOLS_IN_LOGIN = 3
    USER_NOT_FOUND = 4
    INCORRECT_PASSWORD = 5
    INCORRECT_SYNTAX = 6
    USER_ALREADY_EXISTS = 7
    DO_NOT_NEED_UPDATE = 8


@app.route('/api')
def api():
    return render_template(
        'api.html',
        title='API'
    )


@app.route('/api/get-token')
def api_get_token():
    login = request.args.get('login')
    password = request.args.get('password')

    user = User.find_by_login(login)

    ret_code = BaseFunctions.which_is_none(
        [login, password, user],
        [
            API_CODES.INCORRECT_SYNTAX,
            API_CODES.INCORRECT_SYNTAX,
            API_CODES.USER_NOT_FOUND
        ]
    )

    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    if user.password != password:
        return json.dumps({'code': API_CODES.INCORRECT_PASSWORD}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token}, ensure_ascii=False)


@app.route('/api/get-login-password')
def api_get_login_password():
    token = request.args.get('token')

    user = User.find_by_token(token)

    ret_code = BaseFunctions.which_is_none(
        [token, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    )

    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'login': user.login, 'password': user.password}, ensure_ascii=False)


@app.route('/api/signup')
def api_signup():
    login = request.args.get('login')
    password = request.args.get('password')
    keyword = request.args.get('keyword')

    user_created_previously = User.find_by_login(login)

    ret_code = BaseFunctions.which_is_none(
        [login, password, keyword, user_created_previously],
        [API_CODES.INCORRECT_SYNTAX] * 3 + [API_CODES.USER_ALREADY_EXISTS]
    )
    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)
    elif ';' in login:
        return json.dumps({'code': API_CODES.FORBIDDEN_SYMBOLS_IN_LOGIN, 'symbol': ';'}, ensure_ascii=False)

    user = User(login, password, keyword)
    BaseFunctions.sign_up(user)

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token}, ensure_ascii=False)


@app.route('/api/get-chats')
def api_get_chats():
    token = request.args.get('token')
    last_time = request.args.get('last-time')

    user = User.find_by_token(token)

    ret_code = BaseFunctions.which_is_none(
        [token, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    )

    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    chats = [
        {
            'id': i.id,
            'members': ';'.join(i.members),
            'name': i.name,
            'time_last_message': i.last_message_time
         } for i in user.get_chats()
    ]

    if str(chats[-1]['time_last_message']) == last_time:
        return json.dumps({'code': API_CODES.DO_NOT_NEED_UPDATE}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'chats': chats}, ensure_ascii=False)


@app.route('/api/create-chat')
def api_create_chat():
    token = request.args.get('token')
    name = request.args.get('name')
    members = request.args.get('members')
    password = request.args.get('password')

    user = User.find_by_token(token)

    ret_code = BaseFunctions.which_is_none(
        [token, name, members, password, user],
        [API_CODES.INCORRECT_SYNTAX] * 4 + [API_CODES.USER_NOT_FOUND]
    )
    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    members = members.split(';')

    curr_chat = BaseFunctions.create_chat(user, name, members, password)
    return json.dumps({'code': API_CODES.SUCCESS, 'chat-id': curr_chat.id}, ensure_ascii=False)


@app.route('/api/recover-password')
def api_recover_password():
    login = request.args.get('login')
    keyword = request.args.get('keyword')

    user = User.find_by_login(login)

    ret_code = BaseFunctions.which_is_none(
        [login, keyword, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    )
    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    if user.keyword != keyword:
        return json.dumps({'code': API_CODES.INCORRECT_PASSWORD}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'password': user.password, 'token': user.token}, ensure_ascii=False)


@app.route('/api/remove-account')
def api_remove_account():
    token = request.args.get('token')

    user = User.find_by_token(token)
    ret_code = BaseFunctions.which_is_none(
        [token, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    ) or API_CODES.SUCCESS

    if ret_code == API_CODES.SUCCESS:
        BaseFunctions.remove_account(user)

    return json.dumps({'code': ret_code}, ensure_ascii=False)


@app.route('/api/change-password')
def api_change_password():
    token = request.args.get('token')
    new_password = request.args.get('password')

    user = User.find_by_token(token)

    ret_code = BaseFunctions.which_is_none(
        [token, new_password, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    ) or API_CODES.SUCCESS

    if ret_code == API_CODES.SUCCESS:
        BaseFunctions.change_password(user, new_password)

    return json.dumps({'code': ret_code}, ensure_ascii=False)


@app.route('/api/chat')
def api_chat():
    token = request.args.get('token')
    id_ = request.args.get('chat-id')
    last_time = request.args.get('last_time')

    user = User.find_by_token(token)
    curr_chat = Chat.from_id(id_)

    ret_code = BaseFunctions.which_is_none(
        [
            token,
            id_,
            user,
            curr_chat
        ],
        [
            API_CODES.INCORRECT_SYNTAX,
            API_CODES.INCORRECT_SYNTAX,
            API_CODES.USER_NOT_FOUND,
            API_CODES.CHAT_NOT_FOUND
        ]
    )

    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    messages = Message.get_messages_from_chat(curr_chat.id)

    messages.sort(key=lambda i: i.time)

    messages = [
        {
            'sender_login': i.from_.login,
            'text': i.text,
            'time': i.time
        }
        for i in messages
    ]

    if messages[-1]['time'] == last_time:
        return json.dumps({'code': API_CODES.DO_NOT_NEED_UPDATE}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'messages': messages}, ensure_ascii=False)


@app.route('/api/send-message')
def send_message():
    token = request.args.get('token')
    chat_id = request.args.get('chat-id')
    text = request.args.get('text')

    user = User.find_by_token(token)
    curr_chat = Chat.from_id(chat_id)

    ret_code = BaseFunctions.which_is_none(
        [token, chat_id, text, user, curr_chat],
        [API_CODES.INCORRECT_SYNTAX] * 3 + [API_CODES.USER_NOT_FOUND, API_CODES.CHAT_NOT_FOUND]
    ) or API_CODES.SUCCESS

    if ret_code == API_CODES.SUCCESS:
        if user.login not in curr_chat.members and user.login != "SYSTEM":
            return json.dumps({'code': API_CODES.NOT_A_CHAT_MEMBER}, ensure_ascii=False)

        if text.startswith('!!'):
            BaseFunctions.execute_message_command(text, curr_chat, user)
        else:
            if text.startswith('`!!'):
                text = text[1:]
            msg = Message(user, text, time.time(), chat_id)
            msg.write_to_db()

    return json.dumps({'code': ret_code}, ensure_ascii=False)


@app.route('/api/change-token')
def api_change_token():
    token = request.args.get('token')

    user = User.find_by_token(token)

    ret_code = BaseFunctions.which_is_none(
        [token, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    ) or API_CODES.SUCCESS

    res = {'code': ret_code}

    if ret_code == API_CODES.SUCCESS:
        user.token = User.generate_new_token()
        user.write_to_db()
        res |= {'token': user.token}

    return json.dumps(res, ensure_ascii=False)


if __name__ == '__main__':
    # io.run(app, host='127.0.0.1', port=5000, debug=True)
    io.run(app, '192.168.0.200', port=5000, debug=True)
    # app.run('192.168.0.200', port=5000, debug=not SERVER)
