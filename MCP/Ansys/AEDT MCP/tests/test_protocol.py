import socketserver
import threading
import unittest

from aedt_socket_protocol import ProtocolError, request, send_message


class EchoHandler(socketserver.BaseRequestHandler):
    def handle(self):
        message = self.request.recv(4096).split(b"\n", 1)[0]
        import json

        payload = json.loads(message.decode("utf-8"))
        send_message(
            self.request,
            {
                "id": payload["id"],
                "ok": True,
                "result": {"method": payload["method"], "params": payload.get("params", {})},
            },
        )


class ErrorHandler(socketserver.BaseRequestHandler):
    def handle(self):
        message = self.request.recv(4096).split(b"\n", 1)[0]
        import json

        payload = json.loads(message.decode("utf-8"))
        send_message(
            self.request,
            {
                "id": payload["id"],
                "ok": False,
                "error": {"message": "bridge refused"},
            },
        )


class ThreadedServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


class ProtocolTests(unittest.TestCase):
    def _serve(self, handler):
        server = ThreadedServer(("127.0.0.1", 0), handler)
        thread = threading.Thread(target=server.serve_forever)
        thread.daemon = True
        thread.start()

        def cleanup():
            server.shutdown()
            thread.join(timeout=2)
            server.server_close()

        self.addCleanup(cleanup)
        return server.server_address

    def test_request_round_trips_json_payload(self):
        host, port = self._serve(EchoHandler)

        result = request(host, port, "ping", {"timeout": 1.0}, timeout=2.0)

        self.assertEqual(result["method"], "ping")
        self.assertEqual(result["params"], {"timeout": 1.0})

    def test_request_raises_bridge_error_message(self):
        host, port = self._serve(ErrorHandler)

        with self.assertRaisesRegex(RuntimeError, "bridge refused"):
            request(host, port, "ping", timeout=2.0)

    def test_mismatched_response_id_is_rejected(self):
        class BadIdHandler(socketserver.BaseRequestHandler):
            def handle(self):
                send_message(self.request, {"id": "wrong", "ok": True, "result": {}})

        host, port = self._serve(BadIdHandler)

        with self.assertRaisesRegex(ProtocolError, "mismatched response id"):
            request(host, port, "ping", timeout=2.0)


if __name__ == "__main__":
    unittest.main()
