import logging

import pytest
import requests

from .server import JsonGet, http_server, JsonPost, Redirect, StaticResources

logging.basicConfig()

PORT = 9999


class TestServer:

    def teardown_method(self, method) -> None:
        if self.server is not None:
            self.server.stop()

    def test_should_call_get_action(self):
        # given
        self._start_http_server(JsonGet("/test", lambda params: {'status': 'ok'}))

        # when
        result = requests.get(f"http://localhost:{PORT}/test")

        # then
        assert 200 == result.status_code
        assert 'ok' == result.json()['status']

    def test_should_call_get_action_with_params(self):
        # given
        self._start_http_server(JsonGet("/test", lambda params: {'params': params}))

        # when
        result = requests.get(f"http://localhost:{PORT}/test?a=0&b=6&b=7")

        # then
        assert 200 == result.status_code
        assert ['0'] == result.json()['params']['a']
        assert ['6', '7'] == result.json()['params']['b']

    def test_should_call_post_action(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'status': 'ok'}))

        # when
        result = requests.post(f"http://localhost:{PORT}/test")

        # then
        assert 200 == result.status_code
        assert 'ok' == result.json()['status']

    def test_should_call_post_action_with_params_and_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'params': params, 'body': body}))

        # when
        result = requests.post(f"http://localhost:{PORT}/test?a=0&b=6&b=7", data='{"hello": "POST BODY"}')

        # then
        assert 200 == result.status_code
        assert ['0'] == result.json()['params']['a']
        assert ['6', '7'] == result.json()['params']['b']
        assert 'POST BODY' == result.json()['body']['hello']

    def test_should_call_post_action_without_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'body': body}))

        # when
        result = requests.post(f"http://localhost:{PORT}/test?a=0&b=6&b=7")

        # then
        assert 200 == result.status_code
        assert '' == result.json()['body']

    def test_should_return_4xx_when_post_action_with_unparsable_body(self):
        # given
        self._start_http_server(JsonPost("/test", lambda params, body: {'body': body}))

        # when
        result = requests.post(f"http://localhost:{PORT}/test", data='non-json string')

        # then
        assert 400 == result.status_code

    def test_should_redirect(self):
        # given
        self._start_http_server(Redirect("/test", "http://example.com"))

        # when:
        result = requests.get(f'http://localhost:{PORT}/test', allow_redirects=False)

        # then
        assert 301 == result.status_code
        assert 'http://example.com' == result.headers['Location']

    @pytest.mark.parametrize("filename, expected_length, expected_content_type", [
        ("text.txt", 9, "text/plain"),
        ("image.png", 81618, "image/png"),
        ("document.pdf", 38078, "application/pdf")
    ])
    def test_should_serve_static_resources(self, filename, expected_length, expected_content_type):
        # given
        self._start_http_server(StaticResources("/static", "./actions_server/test-resources"))

        # when:
        result = requests.get(f'http://localhost:{PORT}/static/{filename}')

        # then
        assert 200 == result.status_code
        assert expected_length == len(result.content)
        assert expected_content_type == result.headers['Content-Type']

    def test_should_serve_static_resources_regardless_slash(self):
        # given
        self._start_http_server(StaticResources("/static/", "./actions_server/test-resources/"))

        # when:
        result = requests.get(f'http://localhost:{PORT}/static/text.txt')

        # then
        assert 200 == result.status_code
        assert 9 == len(result.content)

    def test_should_return_404_if_static_resources_not_found(self):
        # given
        self._start_http_server(StaticResources("/static/", "./actions_server/test-resources"))

        # when:
        result = requests.get(f'http://localhost:{PORT}/static/nonexisting.txt')

        # then
        assert 404 == result.status_code

    def test_should_return_404_if_action_not_found(self):
        # given
        self._start_http_server(JsonGet("/test", lambda params: {'status': 'ok'}))

        # when:
        result = requests.get(f'http://localhost:{PORT}/nonexisting-endpoint')

        # then
        assert 404 == result.status_code

    def test_should_find_action_in_order_of_declaration(self):
        # given
        self._start_http_server([
            JsonGet("/test", lambda params: {'status': '1'}),
            JsonGet("/test", lambda params: {'status': '2'}),
        ])

        # when:
        result = requests.get(f'http://localhost:{PORT}/test')

        # then
        assert 200 == result.status_code
        assert '1' == result.json()['status']

    def _start_http_server(self, actions):
        actions = actions if isinstance(actions, list) else [actions]
        self.server = http_server(PORT, actions, thread_count=1)
        self.server.start(block_caller_thread=False)
