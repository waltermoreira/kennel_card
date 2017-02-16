import eventlet
eventlet.monkey_patch()

import time
import os
import socket
import json

from flask import Flask, render_template, request, redirect, flash
from flask_socketio import SocketIO, send, emit
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, login_required, UserMixin
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


def get_env_var(name):
    try:
        return os.environ[name]
    except KeyError:
        print('Environment variable {0} is needed'.format(name.upper()))
        

PASSWORD = get_env_var('PASSWORD')

login_manager = LoginManager()

app = Flask(__name__)

app.config.update(
    DEBUG = True,
    SECRET_KEY = 'apa!'
)

login_manager.init_app(app)
socketio = SocketIO(app, logger=True, engineio_logger=True)


@app.route('/')
@login_required
def main():
    return render_template('main.html')

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login?next=' + request.path)

@socketio.on('connect', namespace='/apa')
def ws_conn():
    print('Connected {}'.format(request.sid))
#    socketio.emit('msg', {'count': data['connected']}, namespace='/apa')


@socketio.on('disconnect', namespace='/apa')
def ws_disconn():
    print('Disconnected {}'.format(request.sid))
#    socketio.emit('msg', {'count': data['connected']}, namespace='/apa')

@socketio.on('city', namespace='/apa')
def ws_city(message):
    print(message['city'])
    emit('city', {'city': message['city']},
                  namespace="/apa")


class MyForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])

class User(UserMixin):
    pass


@login_manager.user_loader
def user_loader(user_id):
    user = User()
    user.id = 'APA! User'
    return user


@app.route('/login', methods=('GET', 'POST'))
def login():
    form = MyForm()
    if form.validate_on_submit():
        if form.password.data == PASSWORD:
            user = User()
            user.id = 'APA! User'
            login_user(user)
            next_url = request.args.get('next')
            return redirect(next_url or '/')
        else:
            flash('wrong password')
    return render_template('login.html', form=form)


@socketio.on('start', namespace='/apa')
def start(message):
    s = socket.socket()
    s.connect(('172.17.0.1', 9999))
    f = s.makefile('rw')

    def _bg(r, f):
        f.write(json.dumps(message) + '\n')
        f.flush()

        while True:
            line = json.loads(f.readline())
            if line['status'] == 'end':
                print('all done')
                return
            socketio.emit(line['tag'], line, namespace='/apa', room=r)

    eventlet.spawn(_bg, request.sid, f)
        

if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", port=80)
