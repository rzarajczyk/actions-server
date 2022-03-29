import logging
import threading
import time

import requests

from server import JsonGet, http_server

logging.basicConfig()

actions = [
    JsonGet("/test", lambda params: {'status': 'ok'})
]

# =====================================

server = http_server(9999, actions)
server.start(block_caller_thread=False)

result = requests.get("http://localhost:9999/test")
result.raise_for_status()
print(result.json())

server.stop()


# ======================================

class RequestThread(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.server = server

    def run(self):
        time.sleep(5)
        result = requests.get("http://localhost:9999/test")
        result.raise_for_status()
        print(result.json())
        self.server.stop()


server = http_server(9999, actions)

request_thread = RequestThread(server)
request_thread.start()

server.start(block_caller_thread=True)
