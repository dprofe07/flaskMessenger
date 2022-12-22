from app import app


import eventlet
import eventlet.wsgi

eventlet.wsgi.server(eventlet.listen(('127.0.0.1', 8003)), app)
