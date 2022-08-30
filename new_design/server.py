from flask import Flask, render_template, request
from forms import forms

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('guest.html')

@app.route('/form', methods=['GET', 'POST'])
def form():
    formobj = request.form
    print(formobj)
    if len(formobj) != 0:
        return str(formobj)
    args = request.args
    name = args['name']
    form = forms[name]
    return render_template('form.html', form=form, name=name)


if __name__ == '__main__':
    app.run('127.0.0.1', 5000, debug=True)