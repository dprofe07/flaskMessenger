from flask import Flask, render_template
from flask_socketio import SocketIO, send, join_room, emit

app = Flask(__name__)
io = SocketIO(app, cors_allowed_origins='*')


@io.on('message')
def handle_message(data):
    print('Message:', data)
    send(data, to=data['room'])


@io.on('join')
def join(data):
    join_room(data['room'])

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    io.run(app, debug=True, host='192.168.0.200', port=5000)