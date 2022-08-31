from flask import Flask, render_template
from flask_socketio import SocketIO, send

app = Flask(__name__)
io = SocketIO(app, cors_allowed_origins='*')


@io.on('message')
def handle_message(data):
    print('Message:', data)
    send(data, broadcast=True)

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    io.run(app, debug=True)