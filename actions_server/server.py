import json
import logging
import mimetypes
import os
import socket
import threading
import urllib.parse as urlparse
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO

import multipart
from deser import deser


class Response:
    def code(self):
        return 200

    def headers(self) -> dict:
        return {}

    def response_body_bytes(self):
        return "".encode("utf-8")


class ErrorResponse(Response):
    def __init__(self, code, message):
        self._code = code
        self._message = message

    def code(self):
        return self._code

    def headers(self) -> dict:
        return {'Content-type': 'application/json'}

    def response_body_bytes(self):
        return json.dumps({'error': self._message}, indent=4, default=deser.serialize).encode('utf-8')


class RedirectResponse(Response):
    def __init__(self, location):
        self._location = location

    def code(self):
        return 301

    def headers(self) -> dict:
        return {'Location': self._location}


class JsonOkResponse(Response):
    def __init__(self, payload):
        self._payload = payload

    def headers(self) -> dict:
        return {'Content-type': 'application/json'}

    def response_body_bytes(self):
        return json.dumps(self._payload, indent=4, default=deser.serialize).encode('utf-8')


class StaticResourceResponse(Response):
    def __init__(self, mime, data):
        self._mime = mime
        self._data = data

    def headers(self) -> dict:
        return {'Content-type': self._mime}

    def response_body_bytes(self):
        return self._data


class Action:
    def can_handle(self, method, path, params, payload):
        return False

    def handle(self, method, path, params, payload) -> Response:
        return None


class JsonGet(Action):
    def __init__(self, endpoint, callable):
        self.path = endpoint
        self.callable = callable

    def can_handle(self, method, path, params, payload):
        return method == 'GET' and path == self.path

    def handle(self, method, path, params, payload) -> Response:
        output = self.callable(params)
        return JsonOkResponse(output)


class JsonPost(Action):
    def __init__(self, endpoint, callable):
        self.path = endpoint
        self.callable = callable

    def can_handle(self, method, path, params, payload):
        return method == 'POST' and path == self.path

    def handle(self, method, path, params, payload) -> Response:
        if len(payload) > 0:
            try:
                payload = json.loads(payload)
            except Exception as e:
                raise ValidationException(e)
        output = self.callable(params, payload)
        return JsonOkResponse(output)


class ProcessFileUploadThenRedirect(Action):
    def __init__(self, endpoint, callable):
        self.path = endpoint
        self.callable = callable

    def can_handle(self, method, path, params, payload):
        return method == 'POST' and path == self.path

    def handle(self, method, path, params, payload) -> Response:
        extractor = FileUploadExtractor(payload)
        if not extractor.is_file_uploaded():
            raise ValidationException("No uploaded file found")
        location = self.callable(params, extractor.extract_uploaded_files())
        return RedirectResponse(location)


class Redirect(Action):
    def __init__(self, path_from, path_to):
        self.path_from = path_from
        self.path_to = path_to

    def can_handle(self, method, path, params, payload):
        return path == self.path_from

    def handle(self, method, path, params, payload) -> Response:
        return RedirectResponse(self.path_to)


class StaticResources(Action):
    def __init__(self, url_path_prefix, dir):
        self._url_prefix = url_path_prefix
        self._dir = dir
        if not self._url_prefix.endswith('/'):
            self._url_prefix += '/'

    def can_handle(self, method, path, params, payload):
        return method == 'GET' and path.startswith(self._url_prefix) and '/' not in path[len(self._url_prefix):]

    def handle(self, method, path, params, payload) -> Response:
        path = path[len(self._url_prefix):]
        optional_slash = '/' if not self._dir.endswith('/') and not path.startswith('/') else ''
        file = self._dir + optional_slash + path
        if os.path.isfile(file):
            mime, encoding = mimetypes.guess_type(file)
            with open(file, 'rb') as f:
                data = f.read()
            return StaticResourceResponse(mime, data)
        else:
            logging.getLogger('web').info("Static resource %s not found" % file)
            return ErrorResponse(404, "File not found: %s" % path)


class ValidationException(Exception):
    def __init__(self, *args, **kwargs):
        Exception.__init__(self, *args, **kwargs)


class ServerController:
    def __init__(self, threads: list, sock):
        self.threads = threads
        self.sock = sock
        self.semaphore = threading.Semaphore(0)

    def start(self, block_caller_thread: bool = False):
        for thread in self.threads:
            thread.start()
        if block_caller_thread:
            self.semaphore.acquire()

    def stop(self):
        for thread in self.threads:
            thread.prepare_shutdown()
        self.sock.close()
        for thread in self.threads:
            thread.shutdown()
        self.semaphore.release()


class UploadedFile:
    def __init__(self, part: multipart.MultipartPart):
        self.form_name = part.name
        self.original_file_name = part.filename
        self.__part = part

    def save_as(self, path):
        self.__part.save_as(path)


class FileUploadExtractor:
    def __init__(self, payload):
        lines = payload.splitlines()
        if len(lines) > 2 and lines[0].startswith(b'--') and b'Content-Disposition: form-data' in lines[1]:
            self.payload = payload
            self.boundary = lines[0][2:]
        else:
            self.payload = None
            self.boundary = None

    def is_file_uploaded(self):
        return self.payload is not None

    def extract_uploaded_files(self):
        parts = multipart.MultipartParser(BytesIO(self.payload), self.boundary).parts()
        result = {}
        for part in parts:
            result[part.name] = UploadedFile(part)
        return result


def http_server(port: int, actions: list, thread_count: int = 10) -> ServerController:
    logger = logging.getLogger('web')

    logger.info('Starting httpserver on port %s in %s threads' % (port, thread_count))

    socket_address = ('', port)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(socket_address)
    sock.listen(5)

    class ServerThread(threading.Thread):
        def __init__(self, i):
            threading.Thread.__init__(self)
            self.i = i
            self.daemon = False
            self.httpd = None
            self.shutting_down = False

        def run(self):
            self.httpd = HTTPServer(socket_address, RequestHandler, False)

            # Prevent the HTTP server from re-binding every handler.
            # https://stackoverflow.com/questions/46210672/
            self.httpd.socket = sock
            self.httpd.server_bind = self.server_close = lambda self: None

            try:
                self.httpd.serve_forever()
            except Exception as e:
                if not self.shutting_down:
                    raise e

        def prepare_shutdown(self):
            self.shutting_down = True

        def shutdown(self):
            if self.httpd is not None:
                self.httpd.shutdown()

    class RequestHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            logger.debug("Accepted HTTP request %s on thread %s" % (self.path, threading.current_thread().name))
            try:
                path, params = self.__parse(self.path)
                for action in actions:
                    if action.can_handle('GET', path, params, {}):
                        output = action.handle('GET', path, params, {})
                        return self.__respond(output)
                return self.__respond(ErrorResponse(404, "File not found"))
            except ValidationException as e:
                self.__respond(ErrorResponse(400, "URL parse exception: %s" % str(e)))
                logger.error("ValidationException", e)
            except Exception as e:
                self.__respond(ErrorResponse(500, str(e)))
                logger.error("Exception", e)

        def do_POST(self):
            logger.debug("Accepted HTTP request %s on thread %s" % (self.path, threading.current_thread().name))
            try:
                path, params = self.__parse(self.path)
                content_length = int(self.headers['Content-Length']) if 'Content-Length' in self.headers else 0
                payload = self.rfile.read(content_length) if content_length > 0 else ""
                for action in actions:
                    if action.can_handle('POST', path, params, payload):
                        output = action.handle('POST', path, params, payload)
                        return self.__respond(output)
                return self.__respond(ErrorResponse(404, "File not found"))
            except ValidationException as e:
                self.__respond(ErrorResponse(400, "URL parse exception: %s" % str(e)))
                logger.error("ValidationException", e)
            except Exception as e:
                self.__respond(ErrorResponse(500, str(e)))
                logger.error("Exception", e)

        def __respond(self, output):
            code = output.code()
            headers = output.headers()
            payload = output.response_body_bytes()
            logger.debug("Returning HTTP %s %s with payload of %s bytes" % (code, headers, len(payload)))
            self.send_response(code)
            for header in headers:
                self.send_header(header, headers[header])
            self.end_headers()
            self.wfile.write(payload)

        @staticmethod
        def __parse(url):
            try:
                url_parsed = urlparse.urlparse(url)
                url_params = urlparse.parse_qs(url_parsed.query)
                url_path = url_parsed.path
                return url_path, url_params
            except Exception as e:
                raise ValidationException(e)

    threads = [ServerThread(i) for i in range(thread_count)]

    return ServerController(threads, sock)
