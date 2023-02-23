import io
import queue
import random
import string
import subprocess
import tarfile
import time
from threading import Thread

from docker.models.containers import Container

import docker
from config import BASE_URL, INACTIVE_TIMELIMIT, VSCODE_URL_PATTERN
from language_map import language_map
from password import Passwords
from scheduler import ShutdownManager
from viewer import viewer


class MessageHandler:
    def __init__(self):
        self.docker_client = docker.from_env()
        try:
            self.docker_client.networks.get('everyone-runner')
        except docker.errors.NotFound:
            self.docker_client.networks.create('everyone-runner')

        self.tty_running_users = set()
        self.vscode_running_users = set()
        self.passwords = Passwords()
        self.shutdown_jm = ShutdownManager(
            shutdown_func=self.shutdown_user_container,
            inactive_timelimit=INACTIVE_TIMELIMIT,
        )

    def create_user_container(self, user: str) -> Container:
        container = self.docker_client.containers.run(
            image="everyone-runner:universal",
            name=f'everyone-runner-{user}',
            user='1000',
            network='everyone-runner',
            entrypoint='',
            working_dir='/workspace',
            command='sleep infinity',
            detach=True,
            auto_remove=False,
            labels={
                'app.name': 'everyone-runner',
                'app.everyone-runner.user': user
            },
        )
        return container

    def shutdown_user_container(self, user: str):
        try:
            container = self.docker_client.containers.get(
                f'everyone-runner-{user}'
            )
        except docker.errors.NotFound:
            pass
        else:
            container.stop()
        self.tty_running_users.discard(user)
        self.vscode_running_users.discard(user)

    def remove_user_container(self, user: str):
        try:
            container = self.docker_client.containers.get(
                f'everyone-runner-{user}'
            )
        except docker.errors.NotFound:
            pass
        else:
            container.remove(force=True)

    def get_running_user_container(self, user: str) -> Container:
        try:
            container = self.docker_client.containers.get(
                f'everyone-runner-{user}')
        except docker.errors.NotFound:
            return self.create_user_container(user)
        else:
            if container.status != 'running':
                container.start()
            return container

    def put_file(self, container: Container, file_name: str, file_content: str):
        stream = io.BytesIO()
        file_bytes = file_content.encode()
        with tarfile.open(fileobj=stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(file_name)
            tarinfo.size = len(file_bytes)
            tarinfo.mtime = time.time()
            tarinfo.uid = 1000
            tarinfo.gid = 1000
            tarinfo.mode = 0o644
            tar.addfile(tarinfo, io.BytesIO(file_bytes))
        container.put_archive(
            path='/workspace/.code',
            data=stream.getvalue(),
        )

    def exec_in_container(self, container: Container, exec_args: dict, run_id: str):
        _, output = container.exec_run(stream=True, **exec_args)
        return viewer.create_log_viewer(run_id, output)

    def run_language(self, user: str, language: str, code: str) -> tuple[int, str]:
        command = language_map.get(language)
        if command is None:
            return 10005, f'Language {language} not supported'
        container = self.get_running_user_container(user)
        self.shutdown_jm.extend_shutdown_job(user)
        rand_str = random_string(6)
        datetime_str = time.strftime('%Y%m%d%H%M%S', time.localtime())
        run_id = f'{datetime_str}-{user}-{rand_str}'
        filename_noext = f'code-{run_id}'
        filename = f'{filename_noext}.{language}'
        self.put_file(container, filename, code)
        run_command = command.format(
            fileName='/workspace/.code/'+filename,
            dir='/workspace/.code/',
            fileNameWithoutExt=filename_noext,
        )

        exec_args = {
            "cmd": [
                'timeout', '300',
                'bash', '-c',
                f'({run_command}) ; rm -f {filename}',
            ],
            "workdir": '/workspace',
            "user": '1000',
        }
        t = self.exec_in_container(container, exec_args, run_id)

        t.join(10)
        if t.is_alive():
            return 0, '运行时间长，请在网站中查看结果：' + BASE_URL + '/log/' + run_id
        else:
            _, output_list = viewer.get_log_viewer(run_id)
            output = ''.join(output_list).strip()
            if len(output) == 0:
                return 0, '<empty output>'
            if len(output) > 500:
                return 0, '输出过长，请在网站中查看结果：' + BASE_URL + '/log/' + run_id
            return 0, output

    def run_ttyd(self, user: str) -> tuple[int, str]:
        userinfo = self.passwords.get(user)
        if userinfo is None:
            return 0, '请先设置密码' + BASE_URL + '/ttyd/setpassword'
        container = self.get_running_user_container(user)
        self.shutdown_jm.extend_shutdown_job(user)
        if user in self.tty_running_users:
            return 0, '请在网站中继续' + BASE_URL + '/ttyd/user/' + user
        password = userinfo['password']
        user_colon_password = f'{user}:{password}'
        container.exec_run(
            cmd=[
                'ttyd', '-b', f'/ttyd/user/{user}', '-c', user_colon_password, 'bash'
            ],
            workdir='/workspace',
            user='1000',
            detach=True,
        )
        self.tty_running_users.add(user)
        return 0, '请在网站中继续' + BASE_URL + '/ttyd/user/' + user

    def run_vscode(self, user: str):
        userinfo = self.passwords.get(user)
        if userinfo is None:
            return 0, '请先设置密码' + BASE_URL + '/ttyd/setpassword'
        container = self.get_running_user_container(user)
        self.shutdown_jm.extend_shutdown_job(user)
        if user in self.vscode_running_users:
            return 0, '请在网站中继续' + VSCODE_URL_PATTERN.format(user=user)
        password = userinfo['password']
        container.exec_run(
            cmd=[
                'code-server', '--bind-addr', '0.0.0.0:8080'
            ],
            environment={"PASSWORD": password},
            workdir='/workspace',
            user='1000',
            detach=True,
        )
        self.vscode_running_users.add(user)
        return 0, '请在网站中继续' + VSCODE_URL_PATTERN.format(user=user)

    def run_reset(self, user: str) -> tuple[int, str]:
        self.shutdown_user_container(user)
        self.tty_running_users.discard(user)
        self.vscode_running_users.discard(user)
        self.remove_user_container(user)
        return 0, '重置成功'

    def get_help_message(self) -> str:
        return (
            'run [language] [code] 执行代码\n'
            'run ttyd 网页shell\n'
            'run vscode 网页vscode\n'
            'run reset 重置系统\n'
        )

    def run_set_password(self, user: str, gpg_message: str) -> tuple[int, str]:
        process = subprocess.run(
            ['gpg', '--decrypt'],
            input=gpg_message.encode(),
            capture_output=True,
        )
        if process.returncode != 0:
            return 0, 'gpg decrypt failed'
        plaintext = process.stdout.decode().strip()
        args = plaintext.split(':', maxsplit=1)
        if len(args) != 2:
            return 0, 'gpg message not match'
        if args[0] != user:
            return 0, 'gpg message not match'
        password = args[1]
        self.passwords.set(user, password)
        return 0, '密码设置成功'

    def handle(self, user: str, user_input: str) -> tuple[int, str]:
        if not user_input.startswith('run '):
            return 1, 'command not match'
        args = user_input.split(maxsplit=2)
        if len(args) == 2:
            match args[1]:
                case 'ttyd' | 'shell':
                    return self.run_ttyd(user)
                case 'vscode' | 'code':
                    return self.run_vscode(user)
                case 'help' | '-h' | '--help' | '?' | 'usage' | '--usage':
                    return 0, self.get_help_message()
                case 'reset':
                    return self.run_reset(user)
                case _:
                    return 0, 'script needed'
        if len(args) != 3:
            return 0, 'command not match'
        if args[1] == 'auth':
            return self.run_set_password(user, args[2])
        return self.run_language(user, args[1], args[2])


def random_string(length: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
