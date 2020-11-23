import socket
from Client import Client

class Server:
    def __init__(self, server_ip, server_port):
        self.ip = server_ip
        self.port = server_port

    def receive(self, sender):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.ip, int(self.port)))
        sender.send(self.ip, self.port)
        data, client_ip_port = sock.recvfrom(1000)
        print(data, client_ip_port)

    def send(self, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
