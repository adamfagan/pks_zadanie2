# ------------------------------------------
# -- FLAG - SEQUENCE -     DATA     - CRC --
# ------------------------------------------
# from tkinter import *
import socket


def handshake(sock, server_ip, server_port):    # SYN = 02, ACK = 01, SYN + ACK = 21
    flag = 2  # SYN
    sequence_num = 1
    header = bytes([flag, sequence_num])
    sock.sendto(header, (server_ip, server_port))
    data, server_ip_port = sock.recvfrom(fragment_size)
    if data.hex()[:2] == "15":  # SYN + ACK
        flag = 1  # ACK
        sequence_num = 3
        header = bytes([flag, sequence_num])
        sock.sendto(header, server_ip_port)

def client_sends_file(server_ip, server_port):
    file_name = "test1.txt"  # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    handshake(sock, server_ip, server_port)
    with open(file_name, "rb") as file:
        while True:
            byte = file.read(fragment_size)
            if not byte:
                break
            sock.sendto(byte, (server_ip, server_port))
            data, server_ip_port = sock.recvfrom(fragment_size)
            print(data)


print("1 -> Klient")
print("2 -> Server")
option = int(input("Zadajte svoju ulohu: "))  # 1 alebo 2
fragment_size = 200  # int(input("Zadajte velkost fragmentu v Bytoch: "))

if option == 1:  # KLIENT
    server_ip = "localhost"  # input("Zadajte cielovu IP adresu: ")
    server_port = 5005  # int(input("Zadajte cielovy port: "))
    print("1 -> Sprava")
    print("2 -> Subor")
    option2 = 2  # int(input("Zadajte svoj vyber: "))
    if option2 == 2:  # KLIENT posiela SUBOR
        client_sends_file(server_ip, server_port)
    elif option2 == 1:  # KLIENT posiela SPRAVU
        message = input("Napiste spravu: ")

elif option == 2:  # SERVER
    server_ip = "localhost"  # input("Zadajte IP adresu: ")
    server_port = 5005  # int(input("Zadajte port: "))
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((server_ip, server_port))
    while True:
        data, client_ip_port = sock.recvfrom(fragment_size)
        if data.hex()[:2] == "02":  # SYN
            flag = 21  # SYN + ACK
            sequence_num = 2
            header = bytes([flag, sequence_num])
            sock.sendto(header, client_ip_port)
        else:
            sock.sendto("Prijate".encode(), client_ip_port)

# b'\x02\x01'
# print(bytes.fromhex(data_hex).decode('utf-8'))

















"""root = Tk()
root.geometry("600x500")
root.title("Zadanie 2")

label_option = Label(root, text="Zadajte ci chcete data vyslat alebo prijat: ")
label = Label(root, text="Zadajte IP adresu prijimatela: ")
entry = Entry(root)
button = Button(root, text="Potvrdit", font=('arial', 10))

entry.config(width=20)
button.config(width=20)

label.grid(row=0, column=0)
entry.grid(row=0, column=1)
button.grid(row=1, column=0)


root.mainloop()"""
