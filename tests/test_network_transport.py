import socket
import threading
import time

from modules.network_client import ChatClient
from modules.network_server import ChatServer
from utils.protocol import encode_message


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


def test_server_handles_multiple_messages_in_one_tcp_stream():
    server = ChatServer(host="127.0.0.1", port=0)
    server.start()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(("127.0.0.1", server.port))

    first = {
        "message_id": "msg-1",
        "timestamp": "2026-09-12T12:00:00Z",
        "author": "usuario1",
        "text": "Primeira",
        "event_type": "chat_message",
        "metadata": {},
    }
    second = {
        "message_id": "msg-2",
        "timestamp": "2026-09-12T12:00:01Z",
        "author": "usuario2",
        "text": "Segunda",
        "event_type": "chat_message",
        "metadata": {},
    }

    sock.sendall(encode_message(first) + encode_message(second))

    deadline = time.time() + 2
    while time.time() < deadline and len(server.received_messages) < 2:
        time.sleep(0.05)

    assert [message["message_id"] for message in server.received_messages[:2]] == ["msg-1", "msg-2"]

    sock.close()
    server.stop()
