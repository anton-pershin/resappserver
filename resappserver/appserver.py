from multiprocessing import Process
import socketserver
import collections
import zmq
import json
from importlib import import_module

import resappserver.aux as aux

#WorkerContext = collections.namedtuple('WorkerContext', ['worker', 'proc', 'parent_pipe'])
#Message = collections.namedtuple('Message', ['version', 'type', 'sender_sid', 'receiver_sid', 'body_obj'])
#protoversions = constants_collection(['INITIAL_VERSION'])
#messagetypes = constants_collection(['HANDSHAKE', 'JSON'])

MessageContext = collections.namedtuple('MessageContext', ['client_id', 'worker_id'])
WorkerContext = collections.namedtuple('WorkerContext', ['proc', 'sock'])

class ApplicationServer:
    def __init__(self, config_file=None):
        #config_file
        self._port = 5998
        self._workers = {}
        self._poller = None
        self._handler = RequestHandler(self)
        self._context = zmq.Context()

    def serve(self):
        frontend = self._context.socket(zmq.ROUTER)
        #backend = context.socket(zmq.DEALER)
        frontend.bind('tcp://*:{}'.format(self._port))
        #backend.bind('tcp://*:5560')

        # Initialize poll set
        self._poller = zmq.Poller()
        self._poller.register(frontend, zmq.POLLIN)
        #pollerself._poller.register(backend, zmq.POLLIN)

        while True:
            socks = dict(self._poller.poll(timeout=1000))
            if socks.get(frontend) == zmq.POLLIN: # check messages in frontend
                msg = frontend.recv_multipart()
                msg_contex, body = self._parse_multipart_header(msg)
                if msg_contex.worker_id == '0':
                    reply_msg = self._handle_body(body)
                    frontend.send_multipart(msg[:3] + [reply_msg])
                else:
                    if msg_contex.worker_id not in self._workers:
                        if aux.worker_state_exists(msg_contex.worker_id):
                            self.add_restarted_worker(worker_id)
                        else:
                            raise BadClientMessage('Worker with worker_id "{}" \
                                                   does not exist'.format(msg_contex.worker_id))
                    worker_sock = self._workers[msg_contex.worker_id].sock
                    worker_sock.send_multipart(msg)
                    reply_from_worker = worker_sock.recv_multipart()
                    frontend.send_multipart(reply_from_worker)
            for worker_id, worker in list(self._workers.items()):
                if not worker.proc.is_alive():
                    print('Deleting {}'.format(worker_id))
                    del self._workers[worker_id]
#            for worker_sock in self._worker_conns.values():  # check messages in workers sockets
#                if socks.get(worker_sock) == zmq.POLLIN: 
#                    msg = worker_sock.recv_multipart()
#                    frontend.send_multipart(msg)

    def add_restarted_worker(self, worker_id):
        worker_state = aux.load_worker_state(worker_id)
        print(worker_state)
        self.add_worker(worker_state['worker_name'], worker_id, worker_state, restart=True)

    def add_worker(self, worker_name, worker_id, input_, restart=False):
        worker_module = import_module('resappserver.workers.{}'.format(worker_name))
        #except ImportError:
        #    return {'worker_id' : '0', 'err' : 'No such worker name exists'}
        wproc = Process(target=worker_module.launch, args=(worker_id, input_, restart))
        wproc.start()
        wsock = self._context.socket(zmq.DEALER)
        wsock.connect('ipc://{}.ipc'.format(worker_id))
        self._workers[worker_id] = WorkerContext(wproc, wsock)

    def _parse_multipart_header(self, msg):
        if len(msg) != 4:
            raise BadClientMessage('Message should be multipart with 4 frames \
                (client_id, 0, worker_id and body)')
        msg_contex = MessageContext(msg[0], aux.tostr(msg[2]))
        return msg_contex, msg[3]

    def _handle_body(self, body_bstr):
        body = json.loads(aux.tostr(body_bstr))
        cmd = body['command']
        if cmd not in self._handler.avail_handlers:
            raise BadClientMessage('AppServer request "{}" does not exist'.format(cmd))
        reply = getattr(self._handler, cmd)(body)
        return aux.tobytes(json.dumps(reply))

class RequestHandler(aux.AbstractRequestHandler):
    def __init__(self, appserver):
        super().__init__()
#        self.avail_handlers = [func for func in dir(__class__) \
#                               if callable(getattr(__class__, func)) and not func.startswith('__')]
        self._appserver = appserver

    def create_worker(self, input_):
        worker_id = aux.make_up_worker_id(input_['worker_name'])
        self._appserver.add_worker(input_['worker_name'], worker_id, input_['input'])
        json_reply = {
            'worker_id' : worker_id,
            'err' : 'ok',
        }
        return json_reply

    def get_worker_result(self, input_):
        worker_id = input_['worker_id']
        if aux.worker_result_exists(worker_id): # worker dumped the result and died out
            json_reply = {
                'result' : aux.move_worker_result_to_object(worker_id),
                'err' : 'ok',
            }            
        elif worker_id in self._appserver._workers: # worker is still alive but the result is not dumped
            json_reply = {
                'err' : 'worker is in process',
            }
        elif aux.worker_state_exists(worker_id): # worker is dead, no result is dumped, but there is a saved state
            self._appserver.add_restarted_worker(worker_id) # make the worker alive
            json_reply = {
                'err' : 'worker is in process',
            }
        else:
            json_reply = {
                'err' : 'neither worker nor worker result found',
            }
        return json_reply

    def echo(self, input_):
        json_reply = {
            'output' : input_['input'],
            'err' : 'ok',
        }
        return json_reply