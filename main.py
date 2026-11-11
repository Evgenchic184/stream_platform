import os
import time

from flask import Flask, render_template
from flask_socketio import SocketIO
from werkzeug.middleware.proxy_fix import ProxyFix


def normalize_prefix(value: str) -> str:
    """Return a WSGI-style prefix such as ``/stream`` or an empty string."""
    value = value.strip().strip("/")
    return f"/{value}" if value else ""


class PrefixMiddleware:
    """Set SCRIPT_NAME and strip the prefix if the proxy did not strip it."""

    def __init__(self, wsgi_app, prefix: str):
        self.wsgi_app = wsgi_app
        self.prefix = prefix

    def __call__(self, environ, start_response):
        if self.prefix:
            path = environ.get("PATH_INFO", "")
            if path == self.prefix or path.startswith(f"{self.prefix}/"):
                environ["PATH_INFO"] = path[len(self.prefix) :] or "/"
            environ["SCRIPT_NAME"] = self.prefix
        return self.wsgi_app(environ, start_response)


URL_PREFIX = normalize_prefix(os.environ.get("URL_PREFIX", ""))

app = Flask(__name__)
app.config["APPLICATION_ROOT"] = URL_PREFIX or "/"
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
if URL_PREFIX:
    app.wsgi_app = PrefixMiddleware(app.wsgi_app, URL_PREFIX)
socketio = SocketIO(app)


@app.route("/")
def index():
    try:
        f = open("history", "r")
        info_string = f.readline().strip().split(":")
        title = os.path.basename(info_string[0])
        f.close()
    except:
        title = "history not found"

    time_to_reload = 20 * 60
    time_start = float(info_string[1])
    time_duration = float(info_string[2])
    if time_start != 0 and time_duration != 0:
        time_to_reload = time_start + time_duration - time.time()
    return render_template(
        "index_2.html", title=title, time_to_reload=int((time_to_reload + 10) * 1000)
    )


if __name__ == "__main__":
    # socketio.run(app, host='192.168.0.108', port=5000)
    # socketio.run(app, host='10.0.0.12', port=5000)
    app.run(host="0.0.0.0", port=5000)
