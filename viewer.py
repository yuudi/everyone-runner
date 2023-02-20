import os
from itertools import tee
from threading import Thread
from typing import Iterator

VIER_STATUS_FINISHED = 0
VIER_STATUS_RUNNING = 1
VIER_STATUS_NOT_FOUND = 2


class LogIterator:
    def __init__(self, log: list, iter: Iterator[str]):
        self.log = log
        self.iter = iter

    def start(self, callback: callable = None):
        while line := next(self.iter, None):
            self.log.append(line.decode().strip())
        if callback:
            callback()

    # def fork(self):
    #     fork, self.iter = tee(self.iter)
    #     return fork


class Viewer:
    def __init__(self):
        self.running_viewers: dict[str, LogIterator] = {}

    def create_log_viewer(self, name: str, log_iterator: Iterator[str]):
        v = []
        log_iterator = LogIterator(v, log_iterator)
        self.running_viewers[name] = log_iterator

        t = Thread(
            target=log_iterator.start,
            args=(lambda: self.viewer_finished(name),)
        )
        t.start()
        return t

    def viewer_finished(self, name):
        log_iterator = self.running_viewers.pop(name)
        with open(f'logs/{name}.log', 'w') as f:
            f.write('\n'.join(log_iterator.log))

    def get_log_viewer(self, name, offset=0) -> tuple[int, list[str]]:
        if n := self.running_viewers.get(name):
            if offset >= len(n.log):
                return VIER_STATUS_RUNNING, []
            return VIER_STATUS_RUNNING, n.log[offset:]
        if os.path.exists(f'logs/{name}.log'):
            with open(f'logs/{name}.log') as f:
                lines = f.readlines()
            if offset >= len(lines):
                return VIER_STATUS_FINISHED, []
            return VIER_STATUS_FINISHED, lines[offset:]
        return VIER_STATUS_NOT_FOUND, []


viewer = Viewer()
