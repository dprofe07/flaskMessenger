import time

from flask import Flask, render_template, request, redirect, flash, make_response

from message import Message
from user import User, SERVER


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
    dialoged = []
    if user is not None:
        user.aliases = user.get_aliases(db_data)
        dialoged = user.get_dialoged(db_data)
    return render_template('index.html', user=user, hide_home_link=True, dialoged=dialoged)


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

        if password != password2:
            flash(f'Пароли не совпадают', 'error')
            return render_template('singup.html', login=login, password=password)

        elif User.find_by_login(login, db_data) is not None:
            flash(f'Пользователь с именем "{login}" уже существует.', 'error')
            return render_template('singup.html', login=login, password=password, password2=password2)
        else:
            user = User(login, password, keyword)
            user.write_to_db(db_data)

            flash('Вы успешно зарегистрированы', 'success')

            resp = make_response(render_template('singup.html', redirect_timeout=1000, redirect_address='/'))
            User.save_to_cookies(user, resp)
            return resp
    else:
        return render_template('singup.html')


@app.route('/dialog-to/<login>')
def dialog_to(login):
    curr_user = User.get_from_cookies(request, db_data)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    dialoged_user = User.find_by_login(login, db_data)
    if dialoged_user is None:
        flash('Ваш собеседник не найден в базе данных', 'error')
        return redirect('/')
    messages = (
            Message.get_messages_between(curr_user.login, dialoged_user.login, db_data) +
            Message.get_messages_between(dialoged_user.login, curr_user.login, db_data)
    )

    messages.sort(key=lambda i: i.time)
    return render_template('dialog_to_user.html', user=curr_user, dialoged=dialoged_user, messages=messages)


# noinspection DuplicatedCode
@app.route('/send-message-to/<login>', methods=['POST'])
def send_message_to(login):
    curr_user = User.get_from_cookies(request, db_data)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    dialoged_user = User.find_by_login(login, db_data)
    if dialoged_user is None:
        flash('Ваш собеседник не найден в базе данных', 'error')
        return redirect('/')
    if dialoged_user == curr_user:
        flash('Вы отправили сообщение сами себе. Такие сообщения могут отображаться некорректно', 'warning')
    text = request.form['message']
    new_message = Message(curr_user, dialoged_user, text, time.time())
    new_message.write_to_db(db_data)
    return redirect(f'/dialog-to/{login}')


@app.route('/new-dialog', methods=['POST'])
def new_dialog():
    curr_user = User.get_from_cookies(request, db_data)
    if curr_user is None:
        flash('Войдите в аккаунт, чтобы общаться', 'error')
        return redirect('/')
    login = request.form['login_to']
    user_to = User.find_by_login(login, db_data)
    if user_to is None:
        flash(f'Пользователь с логином {login} не найден', 'error')
        return redirect('/')
    flash('Собеседник будет отображен в ваших диалогах только после написания сообщений')
    return redirect(f'/dialog-to/{login}')


@app.route('/get-messages-div/<login>')
def get_messages_div(login):
    curr_user = User.get_from_cookies(request, db_data)
    dialoged_user = User.find_by_login(login, db_data)
    if dialoged_user is None:
        return (f'''
            <div class="messages-container">
                <div class="message-system">
                    Ошибка! Не удалось найти пользователя с логином {login}.
                </div>
            </div>
        ''')
    messages = (
            Message.get_messages_between(curr_user.login, dialoged_user.login, db_data) +
            Message.get_messages_between(dialoged_user.login, curr_user.login, db_data)
    )

    messages.sort(key=lambda i: i.time)
    a = render_template('messages-div.html', user=curr_user, dialoged=dialoged_user, messages=messages)

    return a


@app.route('/get-dialogs-div')
def get_dialogs_div():
    user = User.get_from_cookies(request, db_data)
    dialoged = user.get_dialoged(db_data)
    return render_template('dialogs-div.html', dialoged=dialoged, user=user)




if __name__ == '__main__':
    app.run('192.168.1.12', port=5000, debug=not SERVER)
