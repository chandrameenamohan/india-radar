#!/usr/bin/env python3
"""Static server for r05-b, with gzip — because Cloudflare Pages serves gzipped
and M1 is a transfer-size measurement.

    python3 serve.py [port]      # default 8742, then 8842, then 8942
"""

import functools
import gzip
import io
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.abspath(__file__))
GZIP = (".html", ".json", ".js", ".css", ".svg")


class Handler(SimpleHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def send_head(self):
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            path = os.path.join(path, "index.html")
        wants = "gzip" in self.headers.get("Accept-Encoding", "")
        if not os.path.isfile(path) or not path.endswith(GZIP) or not wants:
            return super().send_head()
        with open(path, "rb") as fh:
            raw = fh.read()
        buf = io.BytesIO()
        with gzip.GzipFile(fileobj=buf, mode="wb", compresslevel=6, mtime=0) as out:
            out.write(raw)
        body = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", self.guess_type(path))
        self.send_header("Content-Encoding", "gzip")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        return io.BytesIO(body)

    def log_message(self, *args):
        pass


def main():
    ports = [int(sys.argv[1])] if len(sys.argv) > 1 else [8742, 8842, 8942]
    for port in ports:
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", port),
                                      functools.partial(Handler, directory=ROOT))
        except OSError:
            print(f"port {port} is taken, trying the next one")
            continue
        print(f"r05-b on http://127.0.0.1:{port}/")
        srv.serve_forever()
        return
    raise SystemExit(f"no free port in {ports!r}")


if __name__ == "__main__":
    main()
