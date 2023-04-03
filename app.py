#!/usr/bin/python3


import json
import time

import prettytable
from flask import Flask, render_template, request, redirect, flash, send_file, url_for, make_response, abort
from flask_socketio import SocketIO, join_room, rooms

from base_functions import BaseFunctions
from base_unit import BaseUnit
from chat import Chat
from forms import forms
from message import Message
from runtime_storage import storage
from user import User


app = Flask(__name__, storage.prefix + '/static')
io = SocketIO(app, cors_allowed_origins='*', logger=True, engineio_logger=True)

app.config['SECRET_KEY'] = 'fdgdfgdfggf786hfg6hfg6h7f'


@io.on('join')
def handle_join(data):
    join_room(int(data['room']))
    print('JOIN', data)


def socket_send_message(message):
    new_data = {
        'html_sender': message.get_html(message.from_),
        'html_any': message.get_html(None),
        'text': message.text,
        'source': message.from_.token,
        'source_login': message.from_.login,
    }
    io.send(new_data, room=int(message.chat_id))


@io.on('message')
def handle_message(data):
    print('MESSAGE', data)
    user = User.find_by_token(data['source'])

    if user is None:
        return
    curr_chat = Chat.from_id(data['room'])
    if curr_chat is None:
        return

    if user.id not in curr_chat.members and user.login != 'SYSTEM':
        return
    text = data['text']

    if text.startswith('!!'):
        res = BaseFunctions.execute_message_command(
            text,
            curr_chat,
            user,
            lambda message: socket_send_message(message)
        )

        if 'RELOAD' in res:
            io.emit('need_refresh', room=data['room'])

        if 'NEED' in res:
            command = res['command']
            password = command[1]
            msg = Message(
                -1,
                user,
                text.replace(password, '<HIDDEN>'),
                time.time(),
                curr_chat.id
            ).write_to_db()
            socket_send_message(msg)

            sys_user = User.find_by_login_('SYSTEM')
            if sys_user is None:
                msg = Message.send_system_message(
                    'Системный пользователь не создан',
                    curr_chat.id
                )
                socket_send_message(msg)
            else:
                if password != sys_user.password:
                    msg = Message.send_system_message(
                        'Неверный пароль',
                        curr_chat.id
                    )

                    socket_send_message(msg)
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

                        socket_send_message(msg)

                    except BaseException as e:
                        msg = Message.send_system_message(
                            f'Произошла ошибка {e.__class__.__name__}: {e.args}',
                            curr_chat.id
                        )
                        socket_send_message(msg)
    else:
        if text.startswith('`!!'):
            text = text[1:]
        new_message = Message(-1, user, text, time.time(), curr_chat.id)
        new_message.write_to_db()

        socket_send_message(new_message)


@app.route(storage.prefix + '/')
def page_index():
    user = User.get_from_cookies(request)
    if user is None:
        return render_template(
            'guest.html',
            storage=storage,
        )
    else:
        user.aliases = user.get_aliases()
        chats = user.get_chats()
        for chat in chats:
            chat.members_logins = [User.find_by_id(i).login for i in chat.members]
        return render_template(
            'index.html',
            user=user,
            hide_home_link=True,
            chats=chats,
            storage=storage,
        )


@app.route(storage.prefix + '/logout')
def page_logout():
    resp = redirect(url_for('page_index'))
    User.remove_from_cookies(resp)
    return resp


@app.route(storage.prefix + '/remove_account')
def page_remove_account():
    return render_template(
        'remove_account.html',
        user=User.get_from_cookies(request),
        storage=storage
    )


@app.route(storage.prefix + '/remove_account_confirmed')
def page_remove_account_confirmed():
    user = User.get_from_cookies(request)
    resp = redirect(url_for('page_index'))
    if user is not None:
        user.remove_from_cookies(resp)
        user.remove_from_db()
    return resp


@app.route(storage.prefix + '/change_password', methods=['GET', 'POST'])
def page_change_password():
    if request.method == 'GET':
        return render_template(
            "form.html",
            form=forms['change_password'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        old_password = request.form['old_password']
        password = request.form['password']
        password2 = request.form['password2']
        user = User.get_from_cookies(request)
        if user.password != old_password:
            flash('Старый пароль не верен', 'error')
            return render_template(
                "form.html",
                form=forms['change_password'](old_password, password, password2),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        if password != password2:
            flash('Пароли не совпадают', 'error')
            return render_template(
                "form.html",
                form=forms['change_password'](old_password, password),
                user=User.get_from_cookies(request),
                storage=storage,
            )

        BaseFunctions.change_password(user, password)

        flash('Пароль успешно изменён', 'success')
        return redirect(url_for('page_index'))


@app.route(storage.prefix + '/change-login', methods=['GET', 'POST'])
def page_change_login():
    if request.method == 'GET':
        return render_template(
            "form.html",
            form=forms['change_login'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        password = request.form['password']
        new_login = request.form['new_login']

        user = User.get_from_cookies(request)
        if user.password != password:
            flash('Пароль не верен', 'error')
            return render_template(
                "form.html",
                form=forms['change_login'](password, new_login),
                user=user,
                storage=storage,
            )
        if ';' in new_login:
            flash('Точка с запятой не должна присутствовать в логине', 'error')
            return render_template(
                "form.html",
                form=forms['change_login'](password, new_login),
                user=user,
                storage=storage,
            )
        user.login = new_login
        user.write_to_db()

        flash('Логин успешно изменён', 'success')
        return redirect(url_for('page_index'))


@app.route(storage.prefix + '/change-keyword', methods=['GET', 'POST'])
def page_change_keyword():
    if request.method == 'GET':
        return render_template(
            "form.html",
            form=forms['change_keyword'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        password = request.form['password']
        new_keyword = request.form['new_keyword']

        user = User.get_from_cookies(request)
        if user.password != password:
            flash('Пароль не верен', 'error')
            return render_template(
                "form.html",
                form=forms['change_keyword'](password, new_keyword),
                user=user,
                storage=storage,
            )

        user.keyword = new_keyword
        user.write_to_db()

        flash('Логин успешно изменён', 'success')
        return redirect(url_for('page_index'))


@app.route(storage.prefix + '/password_recovery', methods=['GET', 'POST'])
def page_password_recovery():
    if request.method == 'GET':
        return render_template(
            'form.html',
            form=forms['password_recovery'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        login = request.form['login']
        keyword = request.form['keyword']

        user = User.find_by_login_(login)
        if user is None:
            flash(f'Пользователь с логином "{login}" не найден', 'error')
            return render_template(
                'form.html',
                form=forms['password_recovery'](login, keyword),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        if user.keyword != keyword:
            flash(f'Неверное ключевое слово', 'error')
            return render_template(
                'form.html',
                form=forms['password_recovery'](login, keyword),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        password = user.password
        flash('Успешно. Посмотрите ваш пароль в чате SYSTEM', 'success')
        Message.send_system_message(
            f'Ваш пароль: "{password}"',
            [
                i for i in Chat.get_list()
                if i.name == 'DIALOG_BETWEEN/SYSTEM;' + user.login
            ][0].id
        )
        resp = redirect(url_for('page_index'))
        user.save_to_cookies(resp)
        return resp


@app.route(storage.prefix + '/password-recovery-message')
def page_recover_password_message():
    return 'IN_WORK'
    # TODO


# noinspection PyUnusedLocal
@app.errorhandler(404)
def page_err404(e):
    return render_template(
        'error.html',
        msg='Страница не найдена',
        user=User.get_from_cookies(request),
        storage=storage,
    ), 404


# noinspection PyUnusedLocal
@app.errorhandler(500)
def page_err500(e):
    return render_template(
        'error.html',
        msg='Ошибка 500. Сообщите, пожалуйста, действия, которые привели к этой ошибке,'
            ' в сообщениях пользователю SYSTEM',
        user=User.get_from_cookies(request),
        storage=storage,
    ), 500


@app.route(storage.prefix + '/auth', methods=['POST', 'GET'])
def page_auth():
    if User.get_from_cookies(request) is not None:
        return redirect(url_for('page_index'))

    if request.method == 'GET':
        return render_template(
            'form.html',
            form=forms['login'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        login = request.form['login']
        password = request.form['password']
        user = User.find_by_login_(login)
        if user is not None:
            if password == user.password:
                flash('Вы успешно вошли', 'success')

                resp = redirect(url_for('page_index'))
                User.save_to_cookies(user, resp)

                return resp
            else:
                flash(f'Неверный пароль для пользователя "{login}"', 'error')
                return render_template(
                    'form.html',
                    form=forms['login'](login, password),
                    user=User.get_from_cookies(request),
                    storage=storage,
                )
        else:
            flash(f'Пользователь с именем "{login}" не найден.', 'error')
            return render_template(
                'form.html',
                form=forms['login'](login, password),
                user=User.get_from_cookies(request),
                storage=storage,
            )


@app.route(storage.prefix + '/signup', methods=['POST', 'GET'])
def page_signup():
    if User.get_from_cookies(request) is not None:
        return redirect(url_for('page_index'))
    if request.method == 'GET':
        return render_template(
            'form.html',
            form=forms['register'],
            user=User.get_from_cookies(request),
            storage=storage,
        )
    else:
        login = request.form['login']

        password = request.form['password']
        password2 = request.form['password2']
        keyword = request.form['keyword']
        if ';' in login:
            flash('Нельзя использовать ";" в логине')
            return render_template(
                'form.html',
                form=forms['register'](login, password, password2, keyword),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        elif password != password2:
            flash(f'Пароли не совпадают', 'error')
            return render_template(
                'form.html',
                form=forms['register'](login, password, '', keyword),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        elif User.find_by_login_(login) is not None:
            flash(f'Пользователь с именем "{login}" уже существует.', 'error')
            return render_template(
                'form.html',
                form=forms['register'](login, password, password2, keyword),
                user=User.get_from_cookies(request),
                storage=storage,
            )
        else:
            user = User(-1, login, password, keyword)
            BaseFunctions.sign_up(user)

            flash('Вы успешно зарегистрированы', 'success')

            resp = redirect(url_for('page_index'))
            user.save_to_cookies(resp)
            return resp


@app.route(storage.prefix + '/chat/<id_>')
def page_chat(id_):
    curr_user = User.get_from_cookies(request)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect(url_for('page_index'))
    curr_chat = Chat.from_id(id_)
    if curr_chat is None:
        flash('Чат не найден в базе данных', 'error')
        return redirect(url_for('page_index'))
    if curr_user.id not in curr_chat.members and curr_user.login != 'SYSTEM':
        flash('Вступите в чат, чтобы просмотреть его', 'error')
        return redirect(url_for('page_index'))
    messages = Message.get_messages_from_chat(curr_chat.id)

    messages.sort(key=lambda i: i.time)
    dialog = 'DIALOG_BETWEEN' in curr_chat.name
    if dialog:
        new_name = curr_chat.name.replace('DIALOG_BETWEEN/', '', 1)
        logins = new_name.split(';')
        if curr_user.login in logins:
            logins.remove(curr_user.login)
            other = logins[0]
            curr_chat.show_name = f'Диалог с {other}'
        else:
            curr_chat.show_name = f'Диалог между {logins[0]} и {logins[1]}'
    print([type(i.from_) for i in messages])
    print('---')
    print(curr_user)
    print(curr_chat)
    return render_template(
        'chat.html',
        user=curr_user,
        messages=messages,
        chat=curr_chat,
        storage=storage,
    )


@app.route(storage.prefix + '/change-token')
def page_change_token():
    curr_user = User.get_from_cookies(request)
    if curr_user is None:
        return redirect(url_for('page_index'))
    curr_user.token = User.generate_new_token()
    curr_user.write_to_db()
    resp = redirect(url_for('page_index'))
    curr_user.save_to_cookies(resp)
    flash('Вы вышли на всех устройствах', 'success')
    return resp


@app.route(storage.prefix + '/new-chat', methods=['POST'])
def page_new_chat():
    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect(url_for('page_index'))
    chat_name = request.form['chat-name']
    if 'DIALOG_BETWEEN' in chat_name:
        flash(f'Недопустимое название чата: "{chat_name}"', 'error')

    curr_chat = BaseFunctions.create_chat(curr_user, chat_name, [])

    return redirect(url_for('page_chat', id_=curr_chat.id))


@app.route(storage.prefix + '/new-dialog', methods=['POST'])
def page_new_dialog():
    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect(url_for('page_index'))
    login = request.form['login']
    if login == curr_user.login:
        flash('Нельзя создать диалог с самим собой. Используйте чат.', 'error')
        return redirect(url_for('page_index'))
    companion_user = User.find_by_login_(login)
    if companion_user is None:
        flash('Пользователь не найден', 'error')
        return redirect(url_for('page_index'))

    curr_chat = Chat(-1, f'DIALOG_BETWEEN/{login};{curr_user.login}', [curr_user.id, companion_user.id])
    curr_chat.write_to_db()

    curr_user.become_admin(curr_chat.id)
    companion_user.become_admin(curr_chat.id)

    Message.send_system_message(
        f'Пользователь {curr_user.login} создал диалог с пользователем {login}',
        curr_chat.id
    )
    return redirect(url_for('page_chat', id_=curr_chat.id))


@app.route(storage.prefix + '/join-chat')
def page_join_chat():
    code = request.args.get('code')
    if code.startswith('http'):
        return redirect(code)

    curr_user = User.get_from_cookies(request)

    if curr_user is None:
        flash('Войдите на сайт чтобы использовать коды-приглашения', 'error')
        return redirect(url_for('page_index'))

    curr_chat = Chat.from_token(code)
    if curr_chat is None:
        flash('Некорректный код-приглашение', 'error')
        return redirect(url_for('page_index'))

    if curr_user.id in curr_chat.members:
        flash('Вы уже состоите в этом чате')
    else:
        curr_chat.members.append(curr_user.id)
        curr_chat.write_to_db()

        Message.send_system_message(
            f'Пользователь {curr_user.login} присоединился к чату по коду-приглашению',
            curr_chat.id
        )
    return redirect(url_for('page_chat', id_=curr_chat.id))


@app.route(storage.prefix + '/download-app')
def page_download_app():
    abort(404)
    return
    return send_file('static/messenger_app.apk', as_attachment=True)


@app.route(storage.prefix + '/about-app')
def page_about_app():
    abort(404)
    return render_template(
        'about-app.html',
        user=User.get_from_cookies(request),
        storage=storage,
    )


@app.route(storage.prefix + '/make-chat-invite-code/<chat_id>')
def chat_command_make_invite_code(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    if user is None or curr_chat is None:
        return redirect(url_for('page_chat', id_=chat_id))

    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    import urllib.parse
    code = curr_chat.token
    io.emit('need_refresh', room=int(chat_id))

    socket_send_message(
        Message.send_system_message(
            f'Сгенерирован код-приглашение: '
            f'<b><a href="{storage.prefix}/join-chat?code={urllib.parse.quote_plus(code)}">{code}</a></b><br/>'
            f'<img src="https://api.qrserver.com/v1/create-qr-code/?size=300x300&data=https://dprofe.ddns.net'
            f'{storage.prefix}/join-chat?code={urllib.parse.quote_plus(code)}" '
            f'alt="QR-код приглашение"/><br/>',
            curr_chat.id
        )
    )

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/reset-chat-invite-code/<chat_id>')
def chat_command_reset_invite_code(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    if user is None or curr_chat is None:
        return redirect(url_for('page_chat', id_=chat_id))

    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    curr_chat.change_token()
    socket_send_message(
        Message.send_system_message(
            'Предыдущие коды приглашения больше недействительны',
            curr_chat.id
        )
    )

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/add-user-to-chat/<chat_id>')
def chat_command_add_user(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    login = request.args.get('login')
    adding_user = User.find_by_login_(login)

    if adding_user is None:
        flash(f'Пользователь с логином {login} не найден', 'error')

    if user is None or curr_chat is None or adding_user is None:
        return redirect(url_for('page_chat', id_=chat_id))

    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    if adding_user.id in curr_chat.members:
        flash('Пользователь уже добавлен', 'warning')

    else:
        curr_chat.members.append(adding_user.id)
        curr_chat.write_to_db()
        socket_send_message(
            Message.send_system_message(
                f'Пользователь {user.login} добавил пользователя {login}',
                curr_chat.id
            )
        )

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/make-user-admin/<chat_id>')
def chat_command_make_admin(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    login = request.args.get('login')
    new_admin = User.find_by_login_(login)

    if new_admin is None:
        flash(f'Пользователь с логином {login} не найден', 'error')

    if user is None or curr_chat is None or new_admin is None:
        return redirect(url_for('page_chat', id_=chat_id))

    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    if new_admin.id in curr_chat.get_admins():
        flash('Пользователь уже администратор', 'warning')

    else:
        new_admin.become_admin(curr_chat.id)

        socket_send_message(
            Message.send_system_message(
                f'Пользователь {user.login} назначил пользователя {login} администратором',
                curr_chat.id
            )
        )

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/remove-user-from-chat/<chat_id>')
def chat_command_remove_user(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    login = request.args.get('login')
    deleting_user = User.find_by_login_(login)

    if deleting_user is None:
        flash(f'Пользователь с логином {login} не найден', 'error')

    if user is None or curr_chat is None or deleting_user is None:
        return redirect(url_for('page_chat', id_=chat_id))

    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    if deleting_user.id not in curr_chat.members:
        flash('Пользователь не состоит в чате', 'warning')
        return redirect(url_for('page_chat', id_=chat_id))

    curr_chat.members.remove(deleting_user.id)
    deleting_user.stop_being_admin(curr_chat.id)
    curr_chat.write_to_db()

    socket_send_message(
        Message.send_system_message(
            f'Пользователь {user.login} удалил из чата пользователя {login}',
            curr_chat.id
        )
    )

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/rename-chat/<chat_id>')
def chat_command_rename_chat(chat_id):
    name = request.args.get('new-name')

    user = User.get_from_cookies(request)
    chat = Chat.from_id(chat_id)
    if name is None:
        flash('Новое имя не указано', 'error')
    if user is None or chat is None or name is None:
        return redirect(url_for('page_chat', id_=chat_id))

    socket_send_message(
        Message.send_system_message(
            f'Пользователь {user.login} переименовал чат {chat.name} -> {name}',
            chat.id
        )
    )

    chat.name = name
    chat.write_to_db()

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/remove-admin/<chat_id>')
def chat_command_remove_admin(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    login = request.args.get('login')
    old_admin = User.find_by_login_(login)

    if old_admin is None:
        flash(f'Пользователь с логином {login} не найден', 'error')

    if user is None or curr_chat is None or old_admin is None:
        return redirect(url_for('page_chat', id_=chat_id))

    elif not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    elif old_admin.id not in curr_chat.get_admins():
        flash('Пользователь не администратор, или не состоит в этом чате', 'warning')

    else:
        socket_send_message(
            Message.send_system_message(
                f'Пользователь {user.login} удалил из администраторов пользователя {login}',
                curr_chat.id
            )
        )

        old_admin.stop_being_admin(curr_chat.id)

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/clear-chat/<chat_id>')
def chat_command_clear_chat(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    if user is None or curr_chat is None:
        return redirect(url_for('page_chat', id_=chat_id))
    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    curr_chat.clear_messages()
    socket_send_message(
        Message.send_system_message(
            f'Чат очищен пользователем {user.login}',
            curr_chat.id
        )
    )
    io.emit('need_refresh', room=int(chat_id))

    return redirect(url_for('page_chat', id_=chat_id))


@app.route(storage.prefix + '/remove-chat/<chat_id>')
def chat_command_remove_chat(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    if user is None or curr_chat is None:
        return redirect(url_for('page_chat', id_=chat_id))
    if not user.is_admin(curr_chat.id):
        flash('Нужны права администратора', 'error')
        return redirect(url_for('page_chat', id_=chat_id))

    socket_send_message(
        Message.send_system_message(
            f'Чат удалён пользователем {user.login}',
            curr_chat.id
        )
    )

    io.emit('need_refresh', room=int(chat_id))
    curr_chat.remove_from_db()

    flash('Чат успешно удалён', 'success')

    return redirect(url_for('page_index'))


@app.route(storage.prefix + '/leave-chat/<chat_id>')
def chat_command_leave_chat(chat_id):
    user = User.get_from_cookies(request)
    curr_chat = Chat.from_id(chat_id)

    if user is None or curr_chat is None:
        return redirect(url_for('page_chat', id_=chat_id))

    socket_send_message(
        Message.send_system_message(
            f'Пользователь {user.login} покинул чат',
            curr_chat.id
        )
    )

    curr_chat.members.remove(user.id)
    user.stop_being_admin(curr_chat.id)
    curr_chat.write_to_db()

    flash('Вы покинули чат', 'success')

    return redirect(url_for('page_index'))


@app.route(storage.prefix + '/get-dialogs-div')
def get_dialogs_div():
    user = User.get_from_cookies(request)
    if user is None:
        return '<div class="need-update"></div>'
    chats = user.get_chats()
    for chat in chats:
        chat.members_logins = [User.find_by_id(i).login for i in chat.members]
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


@app.route(storage.prefix + '/api')
def api():
    return render_template(
        'api.html',
        user=User.get_from_cookies(request),
        storage=storage,
    )


@app.route(storage.prefix + '/api/get-token')
def api_get_token():
    login = request.args.get('login')
    password = request.args.get('password')

    user = User.find_by_login_(login)

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


@app.route(storage.prefix + '/api/get-login-password')
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


@app.route(storage.prefix + '/api/signup')
def api_signup():
    login = request.args.get('login')
    password = request.args.get('password')
    keyword = request.args.get('keyword')

    user_created_previously = User.find_by_login_(login)

    ret_code = BaseFunctions.which_is_none(
        [login, password, keyword],
        [API_CODES.INCORRECT_SYNTAX] * 3
    )
    if user_created_previously is not None:
        return json.dumps({'code': API_CODES.USER_ALREADY_EXISTS}, ensure_ascii=False)
    elif ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)
    elif ';' in login:
        return json.dumps({'code': API_CODES.FORBIDDEN_SYMBOLS_IN_LOGIN, 'symbol': ';'}, ensure_ascii=False)

    user = User(-1, login, password, keyword)
    BaseFunctions.sign_up(user)

    return json.dumps({'code': API_CODES.SUCCESS, 'token': user.token}, ensure_ascii=False)


@app.route(storage.prefix + '/api/get-chats')
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


@app.route(storage.prefix + '/api/create-chat')
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

    curr_chat = BaseFunctions.create_chat(user, name, members)
    return json.dumps({'code': API_CODES.SUCCESS, 'chat-id': curr_chat.id}, ensure_ascii=False)


@app.route(storage.prefix + '/api/create-dialog')
def api_create_dialog():
    token = request.args.get('token')
    companion_login = request.args.get('companion-login')

    user = User.find_by_token(token)
    companion_user = User.find_by_login_(companion_login)

    ret_code = BaseFunctions.which_is_none(
        [token, companion_login, user, companion_user],
        [API_CODES.INCORRECT_SYNTAX] * 2 + [API_CODES.USER_NOT_FOUND] * 2
    )

    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    curr_chat = Chat(-1, f'DIALOG_BETWEEN/{companion_login};{user.login}', [user.id, companion_user.id], '')
    curr_chat.write_to_db()
    Message.send_system_message(
        f'Пользователь {user.login} создал диалог с пользователем {companion_login}',
        curr_chat.id
    )

    return json.dumps({'code': API_CODES.SUCCESS, 'chat-id': curr_chat.id}, ensure_ascii=False)


@app.route(storage.prefix + '/api/recover-password')
def api_recover_password():
    login = request.args.get('login')
    keyword = request.args.get('keyword')

    user = User.find_by_login_(login)

    ret_code = BaseFunctions.which_is_none(
        [login, keyword, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    )
    if ret_code is not None:
        return json.dumps({'code': ret_code}, ensure_ascii=False)

    if user.keyword != keyword:
        return json.dumps({'code': API_CODES.INCORRECT_PASSWORD}, ensure_ascii=False)

    return json.dumps({'code': API_CODES.SUCCESS, 'password': user.password, 'token': user.token}, ensure_ascii=False)


@app.route(storage.prefix + '/api/remove-account')
def api_remove_account():
    token = request.args.get('token')

    user = User.find_by_token(token)
    ret_code = BaseFunctions.which_is_none(
        [token, user],
        [API_CODES.INCORRECT_SYNTAX, API_CODES.USER_NOT_FOUND]
    ) or API_CODES.SUCCESS

    if ret_code == API_CODES.SUCCESS:
        user.remove_from_db()

    return json.dumps({'code': ret_code}, ensure_ascii=False)


@app.route(storage.prefix + '/api/change-password')
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


@app.route(storage.prefix + '/api/chat')
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


@app.route(storage.prefix + '/api/send-message')
def api_send_message():
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
        if user.id not in curr_chat.members and user.login != "SYSTEM":
            return json.dumps({'code': API_CODES.NOT_A_CHAT_MEMBER}, ensure_ascii=False)

        if text.startswith('!!'):
            BaseFunctions.execute_message_command(text, curr_chat, user,
                                                  lambda msg: socket_send_message(msg))
        else:
            if text.startswith('`!!'):
                text = text[1:]
            msg = Message(-1, user, text, time.time(), chat_id)
            msg.write_to_db()
            socket_send_message(msg)
    return json.dumps({'code': ret_code}, ensure_ascii=False)


@app.route(storage.prefix + '/api/change-token')
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
    print('Ready!')
    io.run(app, storage.addr, port=storage.port, log_output=True, allow_unsafe_werkzeug=True)
    # app.run('192.168.0.200', port=5000, debug=not SERVER)
