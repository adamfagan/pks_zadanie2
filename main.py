# ------------------------------------------
# -- FLAG - SEQUENCE -     DATA     - CRC --
# ------------------------------------------
# from tkinter import *
import socket
import os

# ACK = 01
# SYN = 02
# INF = 03
# SYN + ACK = 21

def parse_data(data):
    parsed_data = {'flg': int(data.hex()[6:8], 16), 'sqn': int(data.hex()[14:16], 16)}
    num_of_fragments = 0
    index = 22
    while data.hex()[index:index+2] == 'ff':
        num_of_fragments += int(data.hex()[index:index+2], 16)
        index += 2
    num_of_fragments += int(data.hex()[index:index+2], 16)
    parsed_data['frg'] = num_of_fragments
    shift = num_of_fragments / 255
    if shift > int(shift):
        shift = int(shift) + 1
    shift = shift*2
    index = 28 + shift
    file_name = data.hex()[index:]
    parsed_data['fnm'] = bytes.fromhex(file_name).decode("ASCII")
    return parsed_data

def create_header(flag, sequence_num, count_fragments, file_name):
    if flag == "SYN":
        flg = bytes('flg', 'utf-8') + bytes([2])
        sqn = bytes('sqn', 'utf-8') + bytes([sequence_num])
        header = flg + sqn
        return header
    elif flag == "SYN+ACK":
        flg = bytes('flg', 'utf-8') + bytes([21])
        sqn = bytes('sqn', 'utf-8') + bytes([sequence_num])
        header = flg + sqn
        return header
    elif flag == "ACK":
        flg = bytes('flg', 'utf-8') + bytes([1])
        sqn = bytes('sqn', 'utf-8') + bytes([sequence_num])
        header = flg + sqn
        return header
    elif flag == "INF":
        flg = bytes('flg', 'utf-8') + bytes([3])
        sqn = bytes('sqn', 'utf-8') + bytes([sequence_num])
        fragments = []
        while count_fragments > 255:
            fragments.append(int(255))
            count_fragments -= 255
        fragments.append(count_fragments)
        frg = bytes('frg', 'utf-8') + bytes(fragments)
        fnm = bytes('fnm', 'utf-8') + bytes(file_name, 'utf-8')
        header = flg + sqn + frg + fnm
        return header

def count_of_fragments(file_name):
    size_of_file = os.path.getsize(file_name)
    if size_of_file / fragment_size > int(size_of_file / fragment_size):
        return int((size_of_file / fragment_size)) + 1
    else:
        return size_of_file / fragment_size

def handshake(sock, server_ip, server_port):
    header = create_header("SYN", 1, 0, 0)
    sock.sendto(header, (server_ip, server_port))
    data, server_ip_port = sock.recvfrom(fragment_size)
    if data.hex()[6:8] == "15":  # SYN + ACK
        header = create_header("ACK", 3, 0, 0)
        sock.sendto(header, server_ip_port)

def client_sends_file(server_ip, server_port):
    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    file_name = "test1.txt"  # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
    count_fragments = count_of_fragments(file_name)  # zistenie poctu posielanych fragmentov
    handshake(client_sock, server_ip, server_port)  # HANDSHAKE
    header = create_header("INF", 4, count_fragments, file_name)
    client_sock.sendto(header, (server_ip, server_port))  # KLIENT posiela INF
    client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
    with open(file_name, "rb") as file:  # POSIELANIE DAT
        while True:
            byte = file.read(fragment_size)
            # header =
            if not byte:
                break
            client_sock.sendto(byte, (server_ip, server_port))
            data_from_server, server_ip_port = client_sock.recvfrom(fragment_size)
            print(data_from_server)


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
    data, client_ip_port = sock.recvfrom(fragment_size)  # Tu SERVER prijima SYN
    if data.hex()[6:8] == "02":  # SYN
        header = create_header("SYN+ACK", 2, 0, 0)
        sock.sendto(header, client_ip_port)
        data, client_ip_port = sock.recvfrom(fragment_size)  # SERVER ocakava ACK
        if data.hex()[6:8] == "01":  # Prijimam ACK od KLIENTA
            data, client_ip_port = sock.recvfrom(fragment_size)  # SERVER ocakava INF
            # Tu v data dostavam pocet fragmentov a meno suboru
            parsed_data = parse_data(data)
            print(parsed_data)
            # TU SOM SKONCIL, V PARSNUTYCH DATACH MAM POCET FRAGMENTOV (SEQUENCE), NA ZAKLADE TOHO
            # MUSIM ROBIT HLAVICKY DATOVYCH FRAGMENTOV, TAKZE MUSIM ROBIT V HLAVICKE V "SQN" POLE
            # PRETOZE MAM 270 FRAGMENTOV A TIE MUSIM DAT PO 255 DO POLA
            # TAKZE PODLA TOHO TREBA ROBIT HLAVICKY
            header = create_header("ACK", parsed_data["sqn"]+1, 0, 0)  # 5 odstranit a nahradit uz parsnutimi datami
            sock.sendto(header, client_ip_port)
            while True:
                data, client_ip_port = sock.recvfrom(fragment_size)
                sock.sendto("Prijate".encode(), client_ip_port)
    else:
       sock.sendto("Prijate".encode(), client_ip_port)

# b'\x02\x01'
# print(bytes.fromhex(data_hex).decode('utf-8'))




"""size_of_sqn = count_fragments / 255  # urcovanie poctu bytov v hlavicke pre Sequence  2
    if size_of_sqn > int(size_of_sqn):
        size_of_sqn = int(size_of_sqn) + 1
    elif size_of_sqn == 0:
        size_of_sqn = 1"""


"""sqn_array = [0] * size_of_sqn  # [0, 0]
    index = 0
    while sqn_array[index] > 255:
        index += 1"""

"""def create_header(flag, sqn_array, index, sequence_num, count_fragments, file_name):"""

"""    if flag == "SYN":
        sqn_array[index] = 1
        flg = bytes('flg', 'utf-8') + bytes([2])
        sqn = bytes('sqn', 'utf-8') + bytes(sqn_array)
        header = flg + sqn
        return header"""




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
