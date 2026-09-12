import socket
import threading
import time

from modules.network_client import ChatClient
from modules.network_server import ChatServer
from utils.protocol import decode_message


def test_server_and_client_can_exchange_message():
    server = ChatServer(host="127.0.0.1", port=0)
    server.start()

    client = ChatClient(host="127.0.0.1", port=server.port)
    assert client.connect() is True

    message = {
        "message_id": "msg-1",
        "timestamp": "2026-09-12T12:00:00Z",
        "author": "usuario1",
        "text": "Olá!",
        "event_type": "chat_message",
        "metadata": {},
    }

    client.send_message(message)

    deadline = time.time() + 2
    received = None
    while time.time() < deadline:
        if server.received_messages:
            received = server.received_messages[0]
            break
        time.sleep(0.05)

    assert received is not None
    assert received["message_id"] == "msg-1"
    assert received["author"] == "usuario1"
    assert received["text"] == "Olá!"

    client.close()
    server.stop()
