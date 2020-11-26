# ------------------------------------------
# -- FLAG - SEQUENCE -     DATA     - CRC --
# ------------------------------------------
# from tkinter import *
import socket
import os

# ACK = 01
# INF = 02


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

def create_header(flag, sequence_num, count_fragments, fragment_size):
    # FLAG(1B) SEQUENCE(3B) COUNT_OF_FRAGMENTS(3B) FRAGMENT_SIZE(2B)
    #  2            0                 7                   1

    flg = flag.to_bytes(1, 'big')
    sqn = sequence_num.to_bytes(3, 'big')
    cof = count_fragments.to_bytes(3, 'big')
    fgs = fragment_size.to_bytes(2, 'big')
    return flg + sqn + cof + fgs


def calculate_fragments(type_of_input, fragment_size, file_or_msg):
    if type_of_input == 1:  # SPRAVA
        count_of_fragments = len(file_or_msg) / fragment_size
        if count_of_fragments > int(count_of_fragments):
            return int(count_of_fragments) + 1
        else:
            return int(count_of_fragments)
    elif type_of_input == 2:  # SUBOR
        size_of_file = os.path.getsize(file_or_msg)
        if size_of_file / fragment_size > int(size_of_file / fragment_size):
            return int(size_of_file / fragment_size) + 1
        else:
            return int(size_of_file / fragment_size)

def client_sends_msg(fragment_size, server_ip, server_port, type, client_sock, message):
    count_of_fragments = calculate_fragments(type, fragment_size, message)  # zistenie poctu posielanych fragmentov


def client_sends_file(fragment_size, server_ip, server_port, type, client_sock, file_name):
    count_of_name_fragments = calculate_fragments(1, fragment_size, file_name)  # type = 1 -> fragmentuje ako string
    count_of_file_fragments = calculate_fragments(type, fragment_size, file_name)  # zistenie poctu posielanych fragmentov

    header = create_header(2, 0, count_of_name_fragments, fragment_size)  # INF = 2, SQN = 0
    inf_message_file_name = header + (2).to_bytes(1, 'big')  # HEADER + DATA
    client_sock.sendto(inf_message_file_name, (server_ip, server_port))  # KLIENT posiela informacie (INF) SERVERU o pocte fragmentoch s nazvom suboru
    # SKONCIL SOM VYTVORENIM METODY CREATE_HEADER A ODOSLANIM INF FRAGMENTO O MENE SUBORU, POKRACOVAT S
    # PARSOVANIM PRIJATEHO FRAGMENTU NA STRANE SERVERA A ODPOVEDANIM SERVERA
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

def client():
    fragment_size = 1         # int(input("Zadajte velkost fragmentu v Bytoch: "))
    server_ip = "localhost"     # input("Zadajte cielovu IP adresu: ")
    server_port = 5005          # int(input("Zadajte cielovy port: "))
    print("1 -> Sprava")
    print("2 -> Subor")
    type = 2                    # int(input("Zadajte svoj vyber: "))

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if type == 1:  # SPRAVA
        message = "Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS !"  # input
        client_sends_msg(fragment_size, server_ip, server_port, type, client_sock, message)
    elif type == 2:  # SUBOR
        file_name = "test1.txt"     # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
        client_sends_file(fragment_size, server_ip, server_port, type, client_sock, file_name)


def server():
    fragment_size = 1         # int(input("Zadajte velkost fragmentu v Bytoch: "))
    server_ip = "localhost"     # input("Zadajte IP adresu: ")
    server_port = 5005          # int(input("Zadajte port: "))

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((server_ip, server_port))
    data, client_ip_port = server_sock.recvfrom(fragment_size)  # SERVER ocakava INF
    print("prijate")
    parsed_data = parse_data(data)
    print(parsed_data)
    header = create_header("ACK", parsed_data["sqn"] + 1, 0, 0)  # 5 odstranit a nahradit uz parsnutimi datami
    server_sock.sendto(header, client_ip_port)
    while True:
        data, client_ip_port = server_sock.recvfrom(fragment_size)
        server_sock.sendto("Prijate".encode(), client_ip_port)

print("1 -> Klient")
print("2 -> Server")
option = int(input("Zadajte svoju ulohu: "))  # 1 alebo 2
if option == 1:  # KLIENT
    client()
elif option == 2:  # SERVER
    server()


# b'\x02\x01'
# print(bytes.fromhex(data_hex).decode('utf-8'))

# TU SOM SKONCIL, V PARSNUTYCH DATACH MAM POCET FRAGMENTOV (SEQUENCE), NA ZAKLADE TOHO
            # MUSIM ROBIT HLAVICKY DATOVYCH FRAGMENTOV, TAKZE MUSIM ROBIT V HLAVICKE V "SQN" POLE
            # PRETOZE MAM 270 FRAGMENTOV A TIE MUSIM DAT PO 255 DO POLA
            # TAKZE PODLA TOHO TREBA ROBIT HLAVICKY


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
