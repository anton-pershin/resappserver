import threading
from copy import deepcopy
import json
from resappserver.aux import AbstractRequestHandler, init_worker

class TestWorkerRequestHandler(AbstractRequestHandler):
    def __init__(self, worker_thread):
        super().__init__()
        self._worker_thread = worker_thread

    def get_result(self, input={}):
        with self._worker_thread.lock:
            return {'result': '{} {}'.format(self._worker_thread.input['first_word'], self._worker_thread.result)}

class WorkerThread(threading.Thread):
    def __init__(self, worker_id, input_):
        super().__init__()
        self.input = input_
        self.result = ''
        self.lock = threading.Lock()

    def __del__(self):
        print('WorkerThread (test) is finishing...')

    def run(self):
        print('WorkerThread (test) is now running...')
        with self.lock:
            self.result = 'world!'

def launch(worker_id, input_):
    init_worker(WorkerThread, TestWorkerRequestHandler, worker_id, input_)
