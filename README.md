# Actions Server

A very simple, multi-threaded HTTP server.

Mainly designed for a very simple tasks, f.ex. 3 json-based endpoints with a simple logic

It utilizes a concept of "Actions" - the functions that can be executed to provide HTTP response.

## Important note:

This server DOES NOT cover all HTTP functionality. This is intentional and probably will not be changed in the future.

# Usage

```python
from actions_server import *

ACTIONS = [
    JsonGet("/get", lambda params: {"response": "ok from GET action"}),
    JsonPost("/post", lambda params, body: {"response": "ok from POST action"}),
    Redirect("/", "/get"),
    StaticResources("/static", "./src/web")
]

server = http_server(port=80, actions=ACTIONS, thread_count=5)

try:
    server.start(block_caller_thread=True)
finally:
    server.stop()

```

In this example, a server will be started on port 80 and the main thread will be blocked. The server will react on
several requests:

* `curl -X GET "http://localhost:80/get"` will produce `{"response": "ok from GET action"}` response
* `curl -X POST "http://localhost:8080/post` will produce `{"response": "ok from POST action"}` response
* `curl -X GET "http://localhost:80/` will send HTTP 301 Redirect to `http://localhost:80/get"
* `curl -X GET "http://localhost:80/static/aaa.png` will return an image `./src/web/aaa.png`

## Available Actions

### `JsonGet(endpoint, callable)`

Will listen to the endpoint `endpoint`, call `callable(params)` (where params is a dict of arguments; note - values are
always an array!) and convert resulting dict into JSON

### `JsonPost(endpoint, callable, body)`

Will listen to the endpoint `endpoint`, call `callable(params, body)` (where params is a dict of arguments; note -
values are always an array!, and body is a parsed the request body into dict) and convert resulting dict into JSON

### `Redirect(from, to)`

Will send HTTP 301 Redirect

### `StaticResources(path, dir)`

Will server all files from `dir` under path `path`