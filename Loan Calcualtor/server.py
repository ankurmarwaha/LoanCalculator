import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit, parse_qs
from calculator import calculate
from banks import products

ROOT = Path(__file__).parent / 'public'


class Handler(BaseHTTPRequestHandler):
    def send(self, status, body, mime='application/json'):
        if not isinstance(body, bytes):
            body = json.dumps(body, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        url = urlsplit(self.path)
        if url.path == '/api/banks':
            q = parse_qs(url.query)
            try:
                self.send(200, products(q.get('bank', ['cba'])[0], q.get('kind', ['home'])[0]))
            except ValueError as e:
                self.send(400, {'error':str(e)})
            except Exception:
                self.send(502, {'error':'Bank feed unavailable. Try again later or enter a rate from the bank website.'})
            return
        files = {'/':('index.html','text/html; charset=utf-8'), '/app.js':('app.js','text/javascript; charset=utf-8'), '/style.css':('style.css','text/css; charset=utf-8')}
        if url.path not in files:
            self.send(404, {'error':'Not found'})
            return
        filename, mime = files[url.path]
        self.send(200, (ROOT/filename).read_bytes(), mime)

    def do_POST(self):
        if self.path != '/api/calculate':
            self.send(404, {'error':'Not found'})
            return
        try:
            length = int(self.headers.get('Content-Length', '0'))
            if not 0 < length <= 16000:
                raise ValueError('Invalid request size.')
            data = json.loads(self.rfile.read(length))
            if not isinstance(data, dict):
                raise ValueError('Expected input fields.')
            self.send(200, calculate(data))
        except (ValueError, TypeError) as e:
            self.send(400, {'error':str(e)})

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    import os
    host, port = os.environ.get('HOST', '127.0.0.1'), int(os.environ.get('PORT', '8000'))
    print(f'Loanleaf running at http://{host}:{port}', flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
