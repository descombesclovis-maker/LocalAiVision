"""Accept a browser's asset burst while the server is between accept calls."""
import socket
import unittest
from http.server import BaseHTTPRequestHandler

from local_app.server import StudioHTTPServer


class AssetConnectionCapacityTests(unittest.TestCase):
    def test_page_asset_connections_can_queue_without_refusal(self):
        server = StudioHTTPServer(('127.0.0.1', 0), BaseHTTPRequestHandler)
        connections = []
        try:
            # Hold accepts so this checks the listening queue, rather than the
            # speed of the test machine's request threads.
            for _ in range(32):
                connections.append(socket.create_connection(server.server_address, timeout=1))
        finally:
            for connection in connections:
                connection.close()
            server.server_close()


if __name__ == '__main__':
    unittest.main()
