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
