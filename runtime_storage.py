import os

from flask import url_for


class RuntimeStorage:
    def __init__(self, prefix=''):
        self.is_server = os.path.exists('/SERVER/is_server')

        if self.is_server:
            try:
                with open('/SERVER/databases/flaskMessenger/demo_mode.option') as f:
                    self.demo_mode = (f.readline().replace('\n', '') == 'on')
            except FileNotFoundError:
                self.demo_mode = False
                with open('/SERVER/databases/flaskMessenger/demo_mode.option', 'w') as f:
                    f.write('off')
            if self.demo_mode:
                self.database = '/SERVER/databases/flaskMessenger/users_db_demo.db'
            else:
                self.database = '/SERVER/databases/flaskMessenger/users_db.db'
            self.prefix = prefix
            self.port = 8003
            self.addr = '0.0.0.0'

        else:
            self.database = 'users.db'
            self.demo_mode = False
            self.prefix = ''
            self.port = 5000
            self.addr = '0.0.0.0'

    def custom_url_for(self, *a, **kw):
        url = url_for(*a, **kw)
        if not url.startswith(self.prefix):
            url = self.prefix + url
            print('A')
        return url



storage = RuntimeStorage('/messenger')