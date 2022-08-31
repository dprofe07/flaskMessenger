class Option:
    def __init__(self, name, idx, required=True, placeholder='', under='', input_type='text', value=''):
        self.name = name
        self.idx = idx
        self.placeholder = placeholder
        self.under = under
        self.input_type = input_type
        self.required = required
        self.value = value


class Hint:
    def __init__(self, text, href):
        self.text = text
        self.href = href


class Form:
    def __init__(self, options, on_receive, title='Новая форма', submit='Отправить', hint=None):
        self.options = options
        self.on_receive = on_receive
        self.title = title
        self.submit = submit
        self.hint = hint

    def __call__(self, *opt_values):
        if len(opt_values) != len(self.options):
            if len(opt_values) == 0:
                return self(*['' for _ in self.options])
            return self
        new_form = Form(self.options, self.on_receive, self.title, self.submit, self.hint)
        for i in range(len(opt_values)):
            new_form.options[i].value = opt_values[i]
        return new_form


forms = {
    'login': Form([
        Option('Логин', 'login'),
        Option('Пароль', 'password', input_type='password'),
    ], None, title='Авторизация', submit='Войти'),
    'register': Form([
        Option('Логин', 'login'),
        Option('Пароль', 'password'),
        Option('Повторите пароль', 'password2'),
        Option('Кодовое слово', 'keyword', required=False,
               under='Для восстановления пароля')
    ], lambda x: x['login'], title='Регистрация', submit='Создать',
        hint=Hint('Забыли пароль?', '#'))
}