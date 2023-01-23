import os
import json


class Passwords():
    def __init__(self):
        if not os.path.exists('data/passwords.json'):
            with open('data/passwords.json', 'w') as f:
                f.write('{}')
            self.passwords = {}
            return
        with open('data/passwords.json', 'r') as f:
            self.passwords = json.load(f)

    def get(self, user):
        return self.passwords.get(user)

    def set(self, user, password):
        self.passwords[user] = {
            'password': password,
            'active': True,
        }
        with open('data/passwords.json', 'w') as f:
            json.dump(self.passwords, f)
