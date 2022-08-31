from this import d
from flask import Flask, render_template, request
from forms import forms

app = Flask(__name__)

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

@app.route('/chat')
def chat():
    return render_template('chat.html')


if __name__ == '__main__':
    app.run('127.0.0.1', 5000, debug=True)