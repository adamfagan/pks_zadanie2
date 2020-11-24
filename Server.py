import socket
from Client import Client

class Server:
    def __init__(self, server_ip, server_port):
        self.ip = server_ip
        self.port = server_port

    def receive(self, sender, fragment_size):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((self.ip, self.port))
        sender.send()  # Tu treba zacat pracovat s fragmentovanim,...
        while True:
            data, client_ip_port = sock.recvfrom(fragment_size)
            print(data)


    """def send(self, message):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.sendto(self.message.encode(), (server_ip, int(server_port)))"""
