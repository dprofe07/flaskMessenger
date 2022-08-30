class Option:
    def __init__(self, name, idx, required=True, placeholder='', under='', input_type='plain'):
        self.name = name
        self.id = idx
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
        Option('Логин', 'login', required=True),
        Option('Пароль', 'password', required=True),
    ], None, title='Авторизация', submit='Войти'),
    'register': Form([
        Option('Логин', 'login', required=True),
        Option('Пароль', 'password', required=True),
        Option('Повторите пароль', 'password-2', required=True),
        Option('Кодовое слово', 'special-word', required=True,
            under='Для восстановления пароля')
    ], None, title='Регистрация', submit='Создать', 
        hint=Hint('Забыли пароль?', '#'))
}