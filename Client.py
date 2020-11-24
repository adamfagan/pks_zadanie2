import socket

class Client:
    def __init__(self, option, data, fragment_size, server_ip, server_port):
        self.option = option  # 2
        self.data = data  # subor - nazov
        self.fragment_size = fragment_size  # 200
        self.server_ip = server_ip
        self.server_port = server_port

    def send(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.option == 2:  # SUBOR
            # 3-way handshake
            with open(self.data, "rb") as file:
                while True:
                    byte = file.read(self.fragment_size)
                    if not byte:
                        break
                    sock.sendto(byte, (self.server_ip, self.server_port))
        elif self.option == 1:  # SPRAVA zo vstupu
            print("sprava")

    def receive(self, sender):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind()