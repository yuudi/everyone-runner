import io
import queue
import random
import string
import subprocess
import tarfile
import time
from threading import Thread

from docker.models.containers import Container, ExecResult
from password import Passwords
import docker
from language_map import language_map
from scheduler import Scheduler

from config import *


class MessageHandler:
    def __init__(self):
        self.docker_client = docker.from_env()
        try:
            self.docker_client.networks.get('everyone-runner')
        except docker.errors.NotFound:
            self.docker_client.networks.create('everyone-runner')

        self.passwords = Passwords()    
        self.scheduler = Scheduler()  # TODO: shutdown idle containers

    def create_user_container(self, user: str) -> Container:
        container = self.docker_client.containers.run(
            image=BASE_IMAGE,
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
        with tarfile.open(fileobj=stream, mode='w') as tar:
            tarinfo = tarfile.TarInfo(file_name)
            tarinfo.size = len(file_content)
            tarinfo.mtime = time.time()
            tarinfo.uid = 1000
            tarinfo.gid = 1000
            tarinfo.mode = 0o644
            tar.addfile(tarinfo, io.BytesIO(file_content.encode()))
        container.put_archive(
            path='/workspace',
            data=stream.getvalue(),
        )

    def exec_in_container(self, container: Container, exec_args: dict, result_queue: queue.Queue):
        exec_result = container.exec_run(**exec_args)
        result_queue.put(exec_result)

    def rtail_url_from_name(self, name: str) -> str:
        return f'{RTAIL_WEBBASE}/#/streams/{name}'

    def ttyd_url_from_name(self, name: str) -> str:
        return TTYD_WEBBASE.format(user=name)

    def run_language(self, user: str, language: str, code: str) -> tuple[int, str]:
        command = language_map.get(language)
        if command is None:
            return 10005, f'Language {language} not supported'
        container = self.get_running_user_container(user)
        run_id = random_string(6)
        filename_noext = f'.code-{user}-{run_id}'
        filename = f'{filename_noext}.{language}'
        self.put_file(container, filename, code)
        run_command = command.format(
            fileName=filename,
            dir='/workspace/',
            fileNameWithoutExt=filename_noext,
        )
        datetime_str = time.strftime('%Y%m%d%H%M%S', time.localtime())

        exec_args = {
            "cmd": [
                'bash', '-c', f'({run_command}) | rtail -h "{RTAIL_SERVER}" -p "{RTAIL_PORT}" --name "{datetime_str}-{run_id}-{user}" ; rm -f {filename}'
            ],
            "workdir": '/workspace',
            "user": '1000',
        }
        q = queue.Queue()
        t = Thread(target=self.exec_in_container,
                   args=(container, exec_args, q))
        t.start()
        t.join(10)
        if t.is_alive():
            return 0, '运行时间长，请在网站中查看结果：' + self.rtail_url_from_name(f'{datetime_str}-{run_id}-{user}')
        else:
            output = q.get().output.decode()
            if len(output) == 0:
                return 0, '<empty output>'
            if len(output) > 500:
                return 0, '输出过长，请在网站中查看结果：' + self.rtail_url_from_name(f'{datetime_str}-{run_id}-{user}')
            return 0, output

    def run_ttyd(self, user: str) -> tuple[int, str]:
        password = self.passwords.get(user)
        if password is None:
            return 1, '请先设置密码' + self.ttyd_url_from_name('setpassword')
        user_colon_password = f'{user}:{password}'
        container = self.get_running_user_container(user)
        container.exec_run(
            cmd=[
                'ttyd', '-c', user_colon_password, 'bash'
            ],
            workdir='/workspace',
            user='1000',
            detach=True,
        )
        return 0, '请在网站中继续' + self.ttyd_url_from_name(user)
    
    def run_set_password(self, user: str, gpg_message: str) -> tuple[int, str]:
        process = subprocess.run(
            ['gpg', '--decrypt'],
            input=gpg_message.encode(),
            capture_output=True,
        )
        if process.returncode != 0:
            return 1, 'gpg decrypt failed'
        plaintext = process.stdout.decode().strip()
        args = plaintext.split(':',maxsplit=1)
        if len(args) != 2:
            return 1, 'gpg message not match'
        if args[0] != user:
            return 1, 'gpg message not match'
        password = args[1]
        self.passwords.set(user, password)


    def handle(self, user: str, user_input: str) -> tuple[int, str]:
        if not user_input.startswith('run '):
            return 1, 'command not match'
        args = user_input.split(maxsplit=2)
        if len(args) == 2:
            if args[1] == 'ttyd':
                return self.run_ttyd(user)
            else:
                return 1, 'script needed'
        if len(args) != 3:
            return 1, 'command not match'
        if args[1] == 'auth':
            return self.run_set_password(user, args[2])
        return self.run_language(user, args[1], args[2])


def random_string(length: int) -> str:
    return ''.join(random.choice(string.ascii_lowercase + string.digits) for _ in range(length))
