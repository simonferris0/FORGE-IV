import queue
import socketserver
import threading
import json

class EthernetServer:
    def __init__(self, host="0.0.0.0", port=5000):
        self.host = host
        self.port = port
        self.command_queue = queue.Queue()
        self.server = None
        self.server_thread = None

    def start(self):
        ethernet = self

        class RequestHandler(socketserver.StreamRequestHandler):
            def handle(self):
                print(f"Type V connected: {self.client_address}")

                for line in self.rfile:
                    try:
                        message = json.loads(line.decode("utf-8"))
                        response_queue = queue.Queue()

                        ethernet.command_queue.put(
                            (message, response_queue)
                        )

                        response = response_queue.get()

                    except (json.JSONDecodeError, UnicodeDecodeError):
                        response = {
                            "success": False,
                            "error": "Invalid JSON message"
                        }

                    self.wfile.write(
                        (json.dumps(response) + "\n").encode("utf-8")
                    )
                    self.wfile.flush()

                print(f"Type V disconnected: {self.client_address}")

        self.server = socketserver.ThreadingTCPServer(
            (self.host, self.port),
            RequestHandler
        )
        self.server.daemon_threads = True

        self.server_thread = threading.Thread(
            target=self.server.serve_forever,
            daemon=True
        )
        self.server_thread.start()

        print(f"Ethernet server listening on {self.host}:{self.port}")

    def process_commands(self, generator):
        while True:
            try:
                message, response_queue = self.command_queue.get_nowait()
            except queue.Empty:
                break

            try:
                command = message.get("command")

                if command == "start":
                    generator.start()
                    response = {
                        "success": generator.state == "RUNNING",
                        "state": generator.state
                    }

                elif command == "stop":
                    generator.stop()
                    response = {
                        "success": generator.state == "OFF",
                        "state": generator.state
                    }

                elif command == "get_status":
                    response = {
                        "success": True,
                        **generator.get_status()
                    }

                else:
                    response = {
                        "success": False,
                        "error": f"Unknown command: {command}"
                    }

            except Exception as error:
                response = {
                    "success": False,
                    "error": str(error)
                }

            response_queue.put(response)

    def stop(self):
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
            print("Ethernet server stopped")