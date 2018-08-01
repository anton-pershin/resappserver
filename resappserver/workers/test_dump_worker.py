import time
#from resappserver.aux import AbstractWorkerThread, AbstractRequestHandler, init_worker_module, dump_worker_state
import resappserver.aux as aux

aux.init_worker_module(__name__)

class WorkerRequestHandler(aux.AbstractRequestHandler):
    def __init__(self, worker_thread):
        super().__init__()
        self._worker_thread = worker_thread

    def get_last_fibonacci_number(self, input={}):
        with self._worker_thread._lock:
            return {'last_fibonacci_number': self._worker_thread.state['F_ii']}

    def get_result(self, input={}):
        return self.get_last_fibonacci_number()

class WorkerThread(aux.AbstractWorkerThread):
    def __init__(self):
        super().__init__()

    def __del__(self):
        print('WorkerThread (dump) is finishing...')

    def on_started(self):
        print('WorkerThread (dump) is created')
        self.state = {
            'F_i': 0,
            'F_ii': 1,
        }

    def on_restarted(self):
        print('WorkerThread (dump) is restarted')

    def run(self):
        print('WorkerThread (dump) is now running...')
        must_exit = (self.state['F_i'] == 0)
        for i in range(self.iters_number):
            F_iii = self.state['F_ii'] + self.state['F_i']
            with self._lock:
                self.state['F_i'] = self.state['F_ii']
                self.state['F_ii'] = F_iii
            if i % 10 == 0 and i != 0:
                print('Dumping state...')
                aux.dump_worker_state(self)
                if must_exit:
                    print('Oops, worker has suddenly crashed!')
                    return
                time.sleep(5)

        print('Dumping result...')
        aux.dump_worker_result(self.worker_id, self.state)
