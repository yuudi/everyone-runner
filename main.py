from flask import Flask, jsonify, request, send_from_directory, send_file
from handler import MessageHandler

app = Flask(__name__)

_secret = ''
with open('secret.txt', 'r') as f:
    _secret = f.read().strip()


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
    if auth != f'Bearer {_secret}':
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

    result,message = handler.handle(user, command)

    return jsonify({'code': result, 'message': message}), 200

@app.route('/common/setpassword')
def setpassword():
    return send_file('setpassword.html')

@app.route('/public_key.asc')
def public_key():
    return send_file('data/public_key.asc')


if __name__ == '__main__':
    app.run()
