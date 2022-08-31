class Option:
    def __init__(self, name, idx, required=True, placeholder='', under='', input_type='plain'):
        self.name = name
        self.idx = idx
        self.placeholder = placeholder
        self.under = under
        self.input_type = input_type
        self.required = required

class Hint:
    def __init__(self, text, href):
        self.text = text
        self.href = href

class Form:
    def __init__(self, options, on_recieve, title='Новая форма', submit='Отправить', hint=None):
        self.options = options
        self.on_recieve = on_recieve
        self.title = title
        self.submit = submit
        self.hint = hint

forms = {
    'login': Form([
        Option('Логин', 'login'),
        Option('Пароль', 'password'),
    ], None, title='Авторизация', submit='Войти'),
    'register': Form([
        Option('Логин', 'login'),
        Option('Пароль', 'password'),
        Option('Повторите пароль', 'password-2'),
        Option('Кодовое слово', 'special-word', required=False,
            under='Для восстановления пароля')
    ], lambda x: x['login'], title='Регистрация', submit='Создать', 
        hint=Hint('Забыли пароль?', '#'))
}