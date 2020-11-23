import socket

class Client:
    def __init__(self, message):
        self.message = message

    def send(self, server_ip, server_port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(self.message.encode(), (server_ip, int(server_port)))

    def receive(self, sender):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind()