import io
import random
import string
import tarfile
import time

import docker
from docker.models.containers import Container

from language_map import language_map

BASE_IMAGE = 'mcr.microsoft.com/devcontainers/universal:linux'


class MessageHandler:
    def __init__(self):
        self.docker_client = docker.from_env()

    def create_user_container(self, user: str) -> Container:
        container = self.docker_client.containers.run(
            image=BASE_IMAGE,
            name=f'code-runner-{user}',
            user='1000',
            entrypoint='',
            working_dir='/workspace',
            command='sleep infinity',
            detach=True,
            auto_remove=False,
            labels={
                'app.name': 'code-runner',
                'app.code-runner.user': user
            },
        )
        return container

    def get_running_user_container(self, user: str) -> Container:
        try:
            container = self.docker_client.containers.get(
                f'code-runner-{user}')
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
            tar.addfile(tarinfo, io.BytesIO(file_content.encode()))
        container.put_archive(
            path='/workspace',
            data=stream.getvalue(),
        )

    def run_language(self, user: str, language: str, code: str) -> tuple[int, str]:
        command = language_map.get(language)
        if command is None:
            return 10005, f'Language {language} not supported'
        container = self.get_running_user_container(user)
        filename_noext = f'code-{user}-{random_string(6)}'
        filename = f'{filename_noext}.{language}'
        self.put_file(container, filename, code)
        run_command = command.format(
            fileName=filename,
            dir='/workspace',
            fileNameWithoutExt=filename_noext,
        )
        result = container.exec_run(
            cmd=['bash', '-c', run_command],
            workdir='/workspace',
            user='1000',
        )
        container.exec_run(
            cmd=['rm', filename],
            workdir='/workspace',
        )
        return result.exit_code, result.output.decode()

    def handle(self, user: str, user_input: str) -> tuple[int, str]:
        if not user_input.startswith('run '):
            return 1, 'command not match'
        _, language, code = user_input.split(maxsplit=2)
        return self.run_language(user, language, code)


def random_string(length: int) -> str:
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(length))
