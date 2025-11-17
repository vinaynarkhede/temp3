"""Simple HTTP server for testing PyTunnel."""

from http.server import HTTPServer, BaseHTTPRequestHandler
import json
from datetime import datetime


class SimpleHandler(BaseHTTPRequestHandler):
    """Simple HTTP request handler."""

    def log_message(self, format, *args):
        """Log an arbitrary message."""
        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

    def do_GET(self):
        """Handle GET requests."""
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "message": "Hello from PyTunnel!",
            "path": self.path,
            "method": "GET",
            "timestamp": datetime.now().isoformat(),
            "headers": dict(self.headers)
        }

        self.wfile.write(json.dumps(response, indent=2).encode())

    def do_POST(self):
        """Handle POST requests."""
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')

        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

        response = {
            "message": "POST request received",
            "path": self.path,
            "method": "POST",
            "timestamp": datetime.now().isoformat(),
            "received_data": body,
            "headers": dict(self.headers)
        }

        self.wfile.write(json.dumps(response, indent=2).encode())


def run_server(port=3000):
    """Run the simple HTTP server."""
    server_address = ('', port)
    httpd = HTTPServer(server_address, SimpleHandler)
    print(f"Starting server on http://localhost:{port}")
    print(f"Press Ctrl+C to stop")
    print("")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped")
        httpd.shutdown()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    run_server(port)
