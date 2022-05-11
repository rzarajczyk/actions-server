import logging
import threading
import time

import requests

from .server import JsonGet, http_server

logging.basicConfig()

PORT = 9999
SLEEP_TIME = 10


class RequestThenStopThread(threading.Thread):
    def __init__(self, server):
        threading.Thread.__init__(self)
        self.response = None
        self.server = server

    def run(self):
        time.sleep(SLEEP_TIME)
        result = requests.get(f"http://localhost:{PORT}/test")
        result.raise_for_status()
        self.response = result.json()
        self.server.stop()


class TestServer:

    def teardown_method(self, method) -> None:
        if self.server is not None:
            self.server.stop()

    def test_should_block_main_thread(self):
        # given
        time_before_server_start = time.time()

        self.server = http_server(PORT, [JsonGet("/test", lambda params: {'status': 'ok'})], thread_count=2)

        request_thread = RequestThenStopThread(self.server)
        request_thread.start()

        self.server.start(block_caller_thread=True)

        # when
        time_after_server_start = time.time()

        # then
        assert SLEEP_TIME < time_after_server_start - time_before_server_start
        assert 'ok' == request_thread.response['status']
