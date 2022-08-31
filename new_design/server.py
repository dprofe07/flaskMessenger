from flask import Flask, render_template, request
from flask_socketio import SocketIO, send, join_room, emit
from forms import forms

app = Flask(__name__)
io = SocketIO(app, cors_allowed_origins='*')


@app.route('/')
def index():
    return render_template('guest.html')

@app.route('/error')
def error():
    args = request.args
    msg = 'Произошла ошибка по' + \
        ' неизвестной причине' if 'msg' not in args else args['msg']
    return render_template('error.html', msg=msg, title='Ошибка!')

@app.route('/form', methods=['GET', 'POST'])
def form():
    args = request.args
    name = args['name']
    form = forms[name]
    if request.method == 'POST':
        formobj = request.form
        return form.on_recieve(formobj)
    return render_template('form.html', form=form, name=name)

@app.route('/chat/<int:room>')
def chat(room):
    return render_template('chat.html', room=room)

@io.on('join')
def join(data):
    join_room(data['room'])

@io.on('message')
def handle_message(data):
    print('Message:', data)
    send(data, to=data['room'])


if __name__ == '__main__':
    io.run(app, host='127.0.0.1', port=5000, debug=True)