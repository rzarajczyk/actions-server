import logging
import unittest

import requests

from server import JsonGet, http_server, Action, JsonPost, Redirect

logging.basicConfig()

PORT = 9999

r = requests.Session()


class ServerTest(unittest.TestCase):

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.stop()

    def test_should_call_get_action(self):
        # given
        self._start_http_server(JsonGet("/test", lambda params: {'status': 'ok'}))

        # when
        result = r.get(f"http://localhost:{PORT}/test")

        # then
        self.assertEqual(200, result.status_code)
        self.assertEqual('ok', result.json()['status'])

    def test_should_call_get_action_with_params(self):
        # given
        self._start_http_server(JsonGet("/test", lambda params: {'params': params}))

        # when
        result = r.get(f"http://localhost:{PORT}/test?a=0&b=6&b=7")

        # then
        self.assertEqual(200, result.status_code)
        self.assertEqual(['0'], result.json()['params']['a'])
        self.assertEqual(['6', '7'], result.json()['params']['b'])

    def test_should_call_post_action(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'status': 'ok'}))

        # when
        result = r.post(f"http://localhost:{PORT}/test")

        # then
        self.assertEqual(200, result.status_code)
        self.assertEqual('ok', result.json()['status'])

    def test_should_call_post_action_with_params_and_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'params': params, 'body': body}))

        # when
        result = r.post(f"http://localhost:{PORT}/test?a=0&b=6&b=7", data='{"hello": "POST BODY"}')

        # then
        self.assertEqual(200, result.status_code)
        self.assertEqual(['0'], result.json()['params']['a'])
        self.assertEqual(['6', '7'], result.json()['params']['b'])
        self.assertEqual('POST BODY', result.json()['body']['hello'])

    def test_should_call_post_action_without_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'body': body}))

        # when
        result = r.post(f"http://localhost:{PORT}/test?a=0&b=6&b=7")

        # then
        self.assertEqual(200, result.status_code)
        self.assertEqual('', result.json()['body'])

    def test_should_return_4xx_when_post_action_with_unparsable_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'body': body}))

        # when
        result = r.post(f"http://localhost:{PORT}/test", data='non-json string')

        # then
        self.assertEqual(400, result.status_code)

    def test_should_redirect(self):
        # given
        self._start_http_server(Redirect("/test", "http://example.com"))

        # when:
        result = r.get(f'http://localhost:{PORT}/test', allow_redirects=False)

        # then
        self.assertEqual(301, result.status_code)
        self.assertEqual('http://example.com', result.headers['Location'])

    def test_should_return_404_if_action_not_found(self):
        # given
        self._start_http_server([])

        # when:
        result = r.get(f'http://localhost:{PORT}/test')

        # then
        self.assertEqual(404, result.status_code)

    def _start_http_server(self, actions: Action | list[Action]):
        actions = actions if isinstance(actions, list) else [actions]
        self.server = http_server(PORT, actions, thread_count=1)
        self.server.start(block_caller_thread=False)
