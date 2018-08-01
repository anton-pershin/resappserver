import zmq
import unittest
import json
from multiprocessing import Process
import time

from resappserver.appserver import *
from resappserver.aux import tobytes, tostr

def launch_server():
    appserver = ApplicationServer()
    try:
        appserver.serve()
    except (KeyboardInterrupt, SystemExit):
        print('Killing server...')
        pass

class AppServerGoodCheck(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._server_proc = Process(target = launch_server)
        cls._server_proc.start()

    def test_echo(self):
        #p = Process(target = launch_server)
        #p.start()
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, tobytes('TEST_CLIENT_1'))
        socket.connect("tcp://localhost:5998")
        print('[Client 1] -> sending Hello World message')
        json_str = json.dumps({'command': 'echo', 'input': 'Hello world!'})
        socket.send_multipart([tobytes('0'), tobytes(json_str)])
        server_worker_id, msg = socket.recv_multipart()
        self.assertEqual('0', tostr(server_worker_id))
        self.assertEqual({'output': 'Hello world!', 'err': 'ok'}, json.loads(tostr(msg)))
        print('[Client 1] received: "{}"'.format(tostr(msg)))
        #p.join()

#    def test_worker(self):
#        #p = Process(target = launch_server)
#        #p.start()
#        context = zmq.Context()
#        socket = context.socket(zmq.REQ)
#        socket.setsockopt(zmq.IDENTITY, tobytes('TEST_CLIENT_2'))
#        socket.connect("tcp://localhost:5998")
#        print('[Client 2] -> sending Hello message')
#        json_str = json.dumps({'command': 'create_worker', 'worker_name': 'test_worker', 'input': {'first_word': 'Hello'}})
#        socket.send_multipart([tobytes('0'), tobytes(json_str)])
#        pseudo_worker_id, msg = socket.recv_multipart()
#        msg_dict = json.loads(tostr(msg))
#        worker_id = msg_dict['worker_id']
#        print('[Client 2] got worker_id: {}'.format(worker_id))
#        self.assertNotEqual('0', worker_id)
#        self.assertEqual('ok', msg_dict['err'])
#        print('[Client 2] -> asking for result')
#        json_str = json.dumps({'command': 'get_result', 'input': {}})
#        socket.send_multipart([tobytes(worker_id), tobytes(json_str)])
#        real_worker_id, msg = socket.recv_multipart()
#        msg_dict = json.loads(tostr(msg))
#        self.assertEqual(worker_id, tostr(real_worker_id))
#        self.assertEqual('Hello world!', msg_dict['result'])
#        print('[Client 2] received: "{}"'.format(tostr(msg)))

    def test_worker_dump(self):
        #p = Process(target = launch_server)
        #p.start()
        context = zmq.Context()
        socket = context.socket(zmq.REQ)
        socket.setsockopt(zmq.IDENTITY, tobytes('TEST_CLIENT_3'))
        socket.connect("tcp://localhost:5998")
        print('[Client 3] -> sending request for starting Fibonacci worker')
        json_str = json.dumps({'command': 'create_worker', 
                               'worker_name': 'test_dump_worker',
                               'input': 
                                    {'iters_number': 50}
                               })
        socket.send_multipart([tobytes('0'), tobytes(json_str)])
        pseudo_worker_id, msg = socket.recv_multipart()
        msg_dict = json.loads(tostr(msg))
        worker_id = msg_dict['worker_id']
        print('[Client 3] got worker_id: {}'.format(worker_id))
        self.assertNotEqual('0', worker_id)
        self.assertEqual('ok', msg_dict['err'])
        print('[Client 3] -> asking for state')
        json_str = json.dumps({'command': 'get_last_fibonacci_number', 'input': {}})
        socket.send_multipart([tobytes(worker_id), tobytes(json_str)])
        real_worker_id, msg = socket.recv_multipart()
        msg_dict = json.loads(tostr(msg))
        self.assertEqual(worker_id, tostr(real_worker_id))
        print('[Client 3] received: "{}"'.format(tostr(msg)))
        time.sleep(15)
        while True:
            print('[Client 3] -> asking for result')
            json_str = json.dumps({'command' : 'get_worker_result', 'worker_id' : worker_id})
            socket.send_multipart([tobytes('0'), tobytes(json_str)])
            real_worker_id, msg = socket.recv_multipart()
            msg_dict = json.loads(tostr(msg))
            #self.assertEqual(worker_id, tostr(real_worker_id))
            print('[Client 3] received: "{}"'.format(tostr(msg)))
            if msg_dict['err'] == 'ok':
                break
            time.sleep(5)
        self.assertEqual(msg_dict, {'result': {'F_ii': 4052739537881, 'F_i': 2504730781961}, 'err': 'ok'})
if __name__ == '__main__':
    unittest.main()
