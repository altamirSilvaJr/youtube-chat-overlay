"""Cliente TCP para receber mensagens do chat em rede local."""

from __future__ import annotations

import socket

from utils.protocol import encode_message


class ChatClient:
    """Cliente que conecta ao servidor e recebe mensagens do chat."""

    def __init__(self, host: str = "127.0.0.1", port: int = 9000) -> None:
        self.host = host
        self.port = port
        self._socket: socket.socket | None = None

    def connect(self) -> bool:
        """Tenta conectar ao servidor."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            sock.connect((self.host, self.port))
            self._socket = sock
            return True
        except OSError:
            return False

    def send_message(self, message: dict) -> None:
        """Envia uma mensagem para o servidor."""
        if self._socket is None:
            raise ConnectionError("Cliente não está conectado ao servidor.")
        self._socket.sendall(encode_message(message))

    def receive(self, timeout: float = 3.0) -> bytes:
        """Recebe uma mensagem do servidor."""
        if self._socket is None:
            return b""

        self._socket.settimeout(timeout)
        try:
            data = self._socket.recv(4096)
        except socket.timeout:
            return b""

        return data if data else b""

    def close(self) -> None:
        """Fecha a conexão atual."""
        if self._socket is not None:
            self._socket.close()
            self._socket = None
