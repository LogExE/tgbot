import http.server
import socketserver
import os

PORT = 8000


class CustomHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if "/schedule/" in self.path and len(self.path.split('.')) == 1:
            self.path += ".html"
        super().do_GET()


os.chdir(os.path.join(os.path.dirname(__file__), "site"))
with socketserver.TCPServer(("", PORT), CustomHandler) as httpd:
    print("serving at port", PORT)
    httpd.serve_forever()
