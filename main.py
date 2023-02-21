from config import API_SECRET
from flask import Flask, jsonify, request, send_file, send_from_directory

from handler import MessageHandler
from viewer import (VIER_STATUS_FINISHED, VIER_STATUS_NOT_FOUND,
                    VIER_STATUS_RUNNING, viewer)

app = Flask(__name__)


handler = MessageHandler()


@app.route('/')
def no_homepage():
    return '404: Not Found', 404


@app.route('/assets/<path:path>')
def assets(path):
    return send_from_directory('assets', path)


@app.route('/api/v1/commands', methods=['POST'])
def commands():
    auth = request.headers.get('Authorization')
    if auth != f'Bearer {API_SECRET}':
        return jsonify({'code': 10000, 'error': 'Invalid Authorization'}), 401

    if request.content_type != 'application/json':
        return jsonify({'code': 10001, 'error': 'Request Content-Type is not json'}), 400

    try:
        data = request.get_json()
    except:
        return jsonify({'code': 10002, 'error': 'Invalid json'}), 400
    user = data.get('user')
    command = data.get('command')

    if not (isinstance(user, str) and isinstance(command, str)):
        return jsonify({'code': 10003, 'error': 'Arguments must be strings'}), 400

    if not user.isalnum():
        return jsonify({'code': 10004, 'error': 'Invalid username'}), 400

    result, message = handler.handle(user, command)

    return jsonify({'code': result, 'message': message}), 200


@app.route('/ttyd/setpassword', strict_slashes=False)
def setpassword():
    return send_file('setpassword.html')


@app.route('/public_key.asc')
def public_key():
    return send_file('data/public_key.asc')


@app.route('/api/v1/logs/<log_id>')
def logs(log_id):
    offset_str = request.args.get('offset', 0)
    if not offset_str.isnumeric():
        return jsonify({'code': 10006, 'error': 'Invalid offset'}), 400
    offset = int(offset_str)
    status, v = viewer.get_log_viewer(log_id, offset)
    if status == VIER_STATUS_NOT_FOUND:
        return jsonify({'code': 10005, 'error': 'Log not found'}), 404
    if status == VIER_STATUS_FINISHED:
        return jsonify({'code': 0, 'finished': True, 'logs': v}), 200
    if status == VIER_STATUS_RUNNING:
        return jsonify({'code': 0, 'finished': False, 'logs': v}), 200


@app.route('/log/<log_id>')
def log(log_id):
    return send_file('view-log.html')


if __name__ == '__main__':
    app.run()
