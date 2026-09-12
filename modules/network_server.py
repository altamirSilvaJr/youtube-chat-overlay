"""Servidor TCP para envio de mensagens do chat em rede local."""

from __future__ import annotations

import socket
import threading
from typing import Any

from utils.protocol import decode_message, encode_message


class ChatServer:
    """Servidor para receber e retransmitir mensagens do chat."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        self.host = host
        self.port = port
        self.on_message = None
        self._server_socket: socket.socket | None = None
        self._thread: threading.Thread | None = None
        self._clients: list[socket.socket] = []
        self._lock = threading.Lock()
        self._shutdown = threading.Event()
        self.received_messages: list[dict[str, Any]] = []

    def start(self) -> None:
        """Inicia o servidor em uma thread separada."""
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._server_socket.bind((self.host, self.port))
        self._server_socket.listen(5)
        self.port = self._server_socket.getsockname()[1]

        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()

    def _accept_loop(self) -> None:
        if self._server_socket is None:
            return

        self._server_socket.settimeout(1)
        while not self._shutdown.is_set():
            try:
                conn, _ = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with self._lock:
                self._clients.append(conn)

            threading.Thread(target=self._handle_client, args=(conn,), daemon=True).start()

    def _handle_client(self, conn: socket.socket) -> None:
        buffer = b""
        try:
            while True:
                data = conn.recv(4096)
                if not data:
                    break
                buffer += data
                while b"\n" in buffer:
                    raw_message, buffer = buffer.split(b"\n", 1)
                    if not raw_message.strip():
                        continue
                    message = decode_message(raw_message)
                    self.received_messages.append(message)
                    if self.on_message is not None:
                        self.on_message(message)
        except OSError:
            pass
        finally:
            try:
                conn.close()
            except OSError:
                pass
            with self._lock:
                if conn in self._clients:
                    self._clients.remove(conn)

    def send_message(self, message: Any) -> None:
        """Envia uma mensagem para clientes conectados."""
        if self._server_socket is None:
            return

        payload = message
        if isinstance(message, dict):
            encoded = encode_message(message)
        else:
            encoded = str(message).encode("utf-8")

        with self._lock:
            clients = list(self._clients)

        for conn in clients:
            try:
                conn.sendall(encoded)
            except OSError:
                with self._lock:
                    if conn in self._clients:
                        self._clients.remove(conn)

    def stop(self) -> None:
        """Fecha o servidor e desconecta os clientes."""
        self._shutdown.set()
        if self._server_socket is not None:
            self._server_socket.close()
            self._server_socket = None

        for conn in list(self._clients):
            try:
                conn.close()
            except OSError:
                pass
        self._clients.clear()
