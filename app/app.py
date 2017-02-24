import eventlet
eventlet.monkey_patch()

import sys
import time
import os
import socket
import json

from flask import Flask, render_template, request, redirect, flash
from flask import send_from_directory
from flask_socketio import SocketIO, send, emit
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, login_required, UserMixin
from wtforms import StringField, PasswordField
from wtforms.validators import DataRequired


def get_env_vars(*names):
    missing = []
    for name in names:
        try:
            yield os.environ[name]
        except KeyError:
            missing.append(name.upper())
    if missing:
        print('Environment variables {0} are needed'.format(', '.join(missing)))
        sys.exit(1)


PASSWORD, SHEET, FOLDER = get_env_vars('PASSWORD', 'SHEET', 'FOLDER')


login_manager = LoginManager()

app = Flask(__name__)

app.config.update(
    DEBUG = True,
    SECRET_KEY = 'apa!'
)

login_manager.init_app(app)
socketio = SocketIO(app, logger=True, engineio_logger=True)

sock = socket.create_connection(('localhost', 1234))
cards = sock.makefile('rw')

def cards_read():
    line = cards.readline()
    print(f'cards_read: {line}')
    return json.loads(line)

def cards_write(data):
    cards.write(json.dumps(data) + '\n')
    cards.flush()


@app.route('/')
@login_required
def main():
    return render_template(
        'main.html',
        sheet_link='https://docs.google.com/spreadsheets/d/{}'.format(SHEET),
        folder_link='https://drive.google.com/drive/u/1/folders/{}'.format(FOLDER)
    )

@login_manager.unauthorized_handler
def unauthorized_callback():
    return redirect('/login?next=' + request.path)

@socketio.on('connect', namespace='/apa')
def ws_conn():
    print('Connected {}'.format(request.sid))

@socketio.on('disconnect', namespace='/apa')
def ws_disconn():
    print('Disconnected {}'.format(request.sid))

@socketio.on('refresh_dogs', namespace='/apa')
def refresh_dogs():
    def _bg(room):
        cards_write({'tag': 'refresh'})
        result = cards_read()
        cards_write({'tag': 'all_dogs_names'})
        result = cards_read()
        socketio.emit('dogs', {'names': result['all_dogs_names']},
                      namespace='/apa', room=room)
    eventlet.spawn(_bg, request.sid)

@socketio.on('check_download', namespace='/apa')
def check_download(message):
    def _bg(room):
        cards_write({'tag': 'refresh'})
        result = cards_read()
        print('got message: {}'.format(message))
        cards_write({
            'tag': 'generate',
            'names': message['selected']})
        result = cards_read()
        if (result['status'] == 'error'
               and result['exception'] == 'PictureNotFound'):
            socketio.emit('picture_not_found',
                          {'for': result['args']},
                          namespace='/apa', room=room)
        elif (result['status'] == 'error'
              and result['exception'] == 'KeyError'):
            socketio.emit('dog_not_found',
                        {'for': result['args']},
                        namespace='/apa', room=room)
        elif (result['status'] == 'error'
              and result['exception'] == 'Exception'):
            socketio.emit('general_exception',
                        {'for': result['args']},
                        namespace='/apa', room=room)
        else:
            socketio.emit('do_download', namespace='/apa', room=room)

    eventlet.spawn(_bg, request.sid)

@app.route('/download', methods=['POST'])
@login_required
def download():
    return send_from_directory(directory='.', filename='out.pdf')

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


if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", port=80)
