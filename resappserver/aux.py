import zmq
import json
import collections
import traceback
import threading
import datetime
import sys
import os
import pickle

class AbstractRequestHandler():
    def __init__(self):
        self.avail_handlers = [func for func in dir(self) \
                               if callable(getattr(self, func)) and not func.startswith('__')]
        #self.avail_handlers = [func for func in dir(__class__) \
        #                       if callable(getattr(__class__, func)) and not func.startswith('__')]

class AbstractWorkerThread(threading.Thread):
    def __init__(self):
        super().__init__()

    @classmethod
    def create_worker(cls, worker_id, worker_name, input_):
        wt = cls()
        wt.worker_id = worker_id
        wt.worker_name = worker_name
        wt.__dict__.update(input_)
        wt._lock = threading.Lock()
        wt.on_started()
        return wt

    @classmethod
    def create_restarted_worker(cls, input_):
        wt = cls()
        wt.__dict__.update(input_)
        wt._lock = threading.Lock()
        wt.on_restarted()
        return wt

    def on_started(self):
        pass

    def on_restarted(self):
        pass

class BadClientMessage(Exception):
    pass

def constants_collection(const_names, const_values = None):
    ClassName = collections.namedtuple('-'.join(const_names), const_names)
    if const_values == None:
        const_values = list(range(len(const_names)))
    return ClassName(*const_values)

def sum_namedtuple_classes(*args):
    '''Given several nametuple classes, merge them into a new nametuple. Taken from Stack Overflow.'''
    return collections.namedtuple('_', ' '.join(sum(map(lambda t:t._fields, args), ())))

def sum_namedtuple_instances(*args):
    '''Given several nametuple instances, merge them into a new nametuple. Taken from Stack Overflow.'''
    return sum_namedtuple_classes(*args)(*sum(args,()))

def merge_two_dicts(x, y):
    '''Given two dicts, merge them into a new dict as a shallow copy. Taken from Stack Overflow.'''
    z = x.copy()
    z.update(y)
    return z

def tostr(bytes_):
    '''Converts bytes to string assuming utf-8 encoding. Just a shortage, nothing more.'''
    return str(bytes_, encoding='utf-8')

def tobytes(str_):
    '''Converts string to bytes assuming utf-8 encoding. Just a shortage, nothing more.'''
    return bytes(str_, encoding='utf-8')

def init_worker(worker_cls, workerhandler_cls, worker_id, worker_name, input_, restart=False):
    if restart:
        worker_thread = worker_cls.create_restarted_worker(input_)
    else:
        worker_thread = worker_cls.create_worker(worker_id, worker_name, input_)
    worker_thread.start()
    handler = workerhandler_cls(worker_thread)
    context = zmq.Context()
    sock = context.socket(zmq.REP)
    sock.bind('ipc://{}.ipc'.format(worker_id))
    poller = zmq.Poller()
    poller.register(sock, zmq.POLLIN)
    while True:
        socks = dict(poller.poll(timeout=1000))
        if socks.get(sock) == zmq.POLLIN: # check messages in frontend
            msg = sock.recv_multipart()
            msg_input = json.loads(tostr(msg[1]))
            cmd = msg_input['command']
            if cmd not in handler.avail_handlers:
                raise BadClientMessage('Worker request "{}" does not exist'.format(cmd))
            reply = getattr(handler, cmd)(msg_input['input'])
            reply_str = json.dumps(reply)
            sock.send_multipart([msg[0], tobytes(reply_str)])
        if not worker_thread.is_alive():
            break

def make_up_worker_id(worker_name):
    dt = datetime.datetime.today()
    return '{}_{}_{}_{}_{}_{}_{}_{}'.format(worker_name, dt.year, dt.month, dt.day, \
                                             dt.hour, dt.minute, dt.second, dt.microsecond)

def get_worker_state_path(worker_id):
    return os.path.join('dumps', '{}.state'.format(worker_id))

def get_worker_result_path(worker_id):
    return os.path.join('dumps', '{}.result'.format(worker_id))

def worker_state_exists(worker_id):
    return os.path.exists(get_worker_state_path(worker_id))

def worker_result_exists(worker_id):
    return os.path.exists(get_worker_result_path(worker_id))

def remove_worker_state(worker_id):
    worker_state_path = get_worker_state_path(worker_id)
    if os.path.exists(worker_state_path):
        os.remove(worker_state_path)

def remove_worker_result(worker_id):
    worker_result_path = get_worker_result_path(worker_id)
    if os.path.exists(worker_result_path):
        os.remove(worker_result_path)

def dump_worker_state(worker_thread):
    worker_state = {}
    for var_name, var_value in worker_thread.__dict__.items():
        if not var_name.startswith('_') and not callable(var_value):
            worker_state[var_name] = var_value
    with open(get_worker_state_path(worker_state['worker_id']), 'wb') as f:
        pickle.dump(worker_state, f)

#def load_worker_state(worker_thread, worker_id):
#    worker_thread.__dict__.update(read_worker_state_from_dump(worker_id))
#    #with open(os.path.join('dumps', '{}.state'.format(worker_thread.worker_id)), 'r') as f:
#    #    worker_state = pickle.load(f)

def load_worker_state(worker_id):
    with open(get_worker_state_path(worker_id), 'rb') as f:
        return pickle.load(f)

def dump_worker_result(worker_id, result):
    remove_worker_state(worker_id)
    with open(get_worker_result_path(worker_id), 'wb') as f:
        pickle.dump(result, f)

def load_worker_result(worker_id):
    with open(get_worker_result_path(worker_id), 'rb') as f:
        return pickle.load(f)

def move_worker_result_to_object(worker_id):
    result_obj = None
    with open(get_worker_result_path(worker_id), 'rb') as f:
        result_obj = pickle.load(f)
    remove_worker_result(worker_id)
    return result_obj

def init_worker_module(module_name):
    module_obj = sys.modules[module_name]
    def launch_func(worker_id, input_, restart=False):
        worker_name = module_name.split('.')[-1]
        init_worker(module_obj.WorkerThread, module_obj.WorkerRequestHandler, worker_id, worker_name, input_, restart)
    setattr(module_obj, 'launch', launch_func)