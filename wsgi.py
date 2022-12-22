from app import app


import eventlet
import eventlet.wsgi

eventlet.wsgi.server(eventlet.listen(('', 8003)), app)
