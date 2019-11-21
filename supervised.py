from xmlrpc.client import ServerProxy
import logging

LOG_FORMAT = '%(asctime)s %(filename)-15s %(funcName)-15s %(levelname)-8s %(message)s'


class Supervised:

    def __init__(self, process, proxy='http://localhost:9001/RPC2'):
        self.process = process
        self._server = ServerProxy(proxy)
        # Configure logging
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        self._logger = logging.getLogger(self.process)
        stream_handler = logging.StreamHandler()
        self._logger.addHandler(stream_handler)

    def status(self):
        try:
            process = self._server.supervisor.getProcessInfo(self.process)
            if 'statename' in process:
                return process['statename']
            else:
                return None
        except Exception as e:
            logging.error("{} {}".format(self.process, e))

    def start(self):
        try:
            self._server.supervisor.startProcess(self.process)
        except Exception as e:
            logging.error("{} {}".format(self.process, e))

    def stop(self):
        try:
            self._server.supervisor.stopProcess(self.process)
        except Exception as e:
            logging.error("{} {}".format(self.process, e))
