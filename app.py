import json
import time

import prettytable
from flask import Flask, render_template, request, redirect, flash, make_response

from base_unit import SERVER, BaseUnit
from message import Message
from user import User
from chat import Chat
from base_functions import BaseFunctions


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
BaseUnit.db_data = db_data


@app.route('/', methods=['GET', 'POST'])
def index():
    user = User.get_from_cookies(request)
    chats = []
    if user is not None:
        user.aliases = user.get_aliases()
        chats = user.get_chats()
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
    user = User.get_from_cookies(request)
    resp = redirect('/')
    if user is not None:
        user.remove_from_cookies(resp)
        BaseFunctions.remove_account(user)
    return resp


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    if request.method == 'GET':
        return render_template('change_password.html')
    else:
        old_password = request.form['old_password']
        password = request.form['password']
        password2 = request.form['password2']
        user = User.get_from_cookies(request)
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

        BaseFunctions.change_password(user, password)

        flash('Пароль успешно изменён', 'success')
        return render_template('change_password.html')


@app.route('/password_recovery', methods=['GET', 'POST'])
def password_recovery():
    if request.method == 'GET':
        return render_template('password_recovery.html')
    else:
        login = request.form['login']
        keyword = request.form['keyword']

        user = User.find_by_login(login)
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
    if User.get_from_cookies(request) is not None:
        return redirect('/')
    if request.method == 'POST':
        login = request.form['login']
        password = request.form['password']
        user = User.find_by_login(login)
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
    if User.get_from_cookies(request) is not None:
        return redirect('/')
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
        elif User.find_by_login(login) is not None:
            flash(f'Пользователь с именем "{login}" уже существует.', 'error')
            return render_template('singup.html', login=login, password=password, password2=password2)
        else:
            user = User(login, password, keyword)
            BaseFunctions.sign_up(user)

            flash('Вы успешно зарегистрированы', 'success')

            resp = make_response(render_template('singup.html', redirect_timeout=1000, redirect_address='/'))
            user.save_to_cookies(resp)
            return resp
    else:
        return render_template('singup.html')


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
    if curr_user.login not in curr_chat.members:
        if curr_user.login != 'SYSTEM':
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
    return render_template('chat.html', user=curr_user, messages=messages, chat=curr_chat, dialog=dialog)


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
    id_ = int(id_)
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

    a = render_template('messages-div.html', user=curr_user, messages=messages)

    return a


@app.route('/get-dialogs-div')
def get_dialogs_div():
    user = User.get_from_cookies(request)
    chats = user.get_chats()
    return render_template('dialogs-div.html', chats=chats, user=user)


# noinspection PyPep8Naming
class API_CODES:
    NOT_A_CHAT_MEMBER = 'NOT_A_CHAT_MEMBER'
    CHAT_NOT_FOUND = 'CHAT_NOT_FOUND'
    FORBIDDEN_SYMBOLS_IN_LOGIN = 'FORBIDDEN_SYMBOLS_IN_LOGIN'
    SUCCESS = 'SUCCESS'
    USER_NOT_FOUND = 'USER_NOT_FOUND'
    INCORRECT_PASSWORD = 'INCORRECT_PASSWORD'
    INCORRECT_SYNTAX = 'INCORRECT_SYNTAX'
    USER_ALREADY_EXISTS = 'USER_ALREADY_EXISTS'


# noinspection DuplicatedCode
@app.route('/api/get-token/')
def api_get_token():
    login = request.args.get('login')
    password = request.args.get('password')

    if login is None or password is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_login(login)
    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})
    if user.password != password:
        return json.dumps({'code': API_CODES.INCORRECT_PASSWORD})

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token})


@app.route('/api/signup')
def api_signup():
    login = request.args.get('login')
    password = request.args.get('password')
    keyword = request.args.get('keyword')

    if login is None or password is None or keyword is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    if User.find_by_login(login) is not None:
        return json.dumps({'code': API_CODES.USER_ALREADY_EXISTS})
    if ';' in login:
        return json.dumps({'code': API_CODES.FORBIDDEN_SYMBOLS_IN_LOGIN, 'symbol': ';'})
    user = User(login, password, keyword)
    user.write_to_db()

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token})


# noinspection DuplicatedCode
@app.route('/api/get-chats')
def api_get_chats():
    token = request.args.get('token')

    if token is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})

    chats = [{'id': i.id, 'members': ';'.join(i.members), 'name': i.name} for i in
             user.get_chats()]

    return json.dumps({'code': API_CODES.SUCCESS, 'chats': chats})


@app.route('/api/create-chat')
def api_create_chat():
    token = request.args.get('token')
    name = request.args.get('name')
    members = request.args.get('members')
    password = request.args.get('password')

    if token is None or name is None or members is None or password is None:
        print(f'{token=}, {name=}, {members=}, {password=}')
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})
    members = members.split(';')
    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})

    curr_chat = BaseFunctions.create_chat(user, name, members, password)
    return json.dumps({'code': API_CODES.SUCCESS, 'chat-id': curr_chat.id})


# noinspection DuplicatedCode
@app.route('/api/recover-password')
def api_recover_password():
    login = request.args.get('login')
    keyword = request.args.get('keyword')

    if login is None or keyword is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_login(login)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})
    if user.keyword != keyword:
        return json.dumps({'code': API_CODES.INCORRECT_PASSWORD})

    return json.dumps({'code': API_CODES.SUCCESS, 'password': user.password, 'token': user.token})


# noinspection DuplicatedCode
@app.route('/api/remove-account')
def api_remove_account():
    token = request.args.get('token')

    if token is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})

    BaseFunctions.remove_account(user)

    return json.dumps({'code': API_CODES.SUCCESS})


@app.route('/api/change-password')
def api_change_password():
    token = request.args.get('token')
    new_password = request.args.get('password')

    if token is None or new_password is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})

    BaseFunctions.change_password(user, new_password)

    return json.dumps({'code': API_CODES.SUCCESS})


@app.route('/api/chat')
def api_chat():
    token = request.args.get('token')
    id_ = request.args.get('chat-id')

    if token is None or id_ is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})
    curr_chat = Chat.from_id(id_)
    if curr_chat is None:
        return json.dumps({'code': API_CODES.CHAT_NOT_FOUND})
    if user.login not in curr_chat.members:
        return json.dumps({'code': API_CODES.NOT_A_CHAT_MEMBER})
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

    return json.dumps({'code': API_CODES.SUCCESS, 'messages': messages})


# noinspection DuplicatedCode
@app.route('/api/send-message')
def send_message():
    token = request.args.get('token')
    id_ = request.args.get('chat-id')
    text = request.args.get('text')

    if token is None or id_ is None or text is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})
    curr_chat = Chat.from_id(id_)
    if curr_chat is None:
        return json.dumps({'code': API_CODES.CHAT_NOT_FOUND})
    if user.login not in curr_chat.members:
        return json.dumps({'code': API_CODES.NOT_A_CHAT_MEMBER})

    if text.startswith('!!'):
        BaseFunctions.execute_message_command(text, curr_chat, user)
    elif text.startswith('`!!'):
        text = text[1:]
    else:
        msg = Message(user, text, time.time(), id_)
        msg.write_to_db()

    return json.dumps({'code': API_CODES.SUCCESS})


@app.route('/api/change-token')
def api_change_token():
    token = request.args.get('token')

    if token is None:
        return json.dumps({'code': API_CODES.INCORRECT_SYNTAX})

    user = User.find_by_token(token)

    if user is None:
        return json.dumps({'code': API_CODES.USER_NOT_FOUND})

    user.token = User.generate_new_token()
    user.write_to_db()

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token})


if __name__ == '__main__':
    app.run('192.168.1.12', port=5000, debug=not SERVER)
