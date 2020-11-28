# ------------------------------------------
# -- FLAG - SEQUENCE -     DATA     - CRC --
# ------------------------------------------
# from tkinter import *
import socket
import os
import heapq
from random import randint
from threading import Timer

from crc16 import GetCrc16

# ACK = 01
# INF = 02
# ERR = 03
# DAT = 04

def timer():
    print("Neprisla odpoved do 0.5 sekundy")

def check_crc(data):
    original_crc = int.from_bytes(data[0:2], 'big')
    if randint(0, 100) > 50:
        new_crc = GetCrc16(str(123456789))  # Na testovanie CRC
    else:
        new_crc = GetCrc16(str(int.from_bytes(data[2:], 'big')))
    if original_crc == new_crc:
        return 1
    else:
        return 0

def parse_data(data):
    parsed_data = {'crc': int.from_bytes(data[0:2], 'big'), 'flag': int.from_bytes(data[2:3], 'big'),
                   'sequence': int.from_bytes(data[3:6], 'big'), 'count_of_fragments': int.from_bytes(data[6:9], 'big'),
                   'data_size': int.from_bytes(data[9:11], 'big'), 'data': data[11:]}
    return parsed_data

def create_header(flag, sequence_num, count_fragments, data_size):
    # FLAG(1B) SEQUENCE(3B) COUNT_OF_FRAGMENTS(3B) DATA_SIZE(2B)
    #  2            0                 9                   1

    flg = flag.to_bytes(1, 'big')
    sqn = sequence_num.to_bytes(3, 'big')
    cof = count_fragments.to_bytes(3, 'big')
    fgs = data_size.to_bytes(2, 'big')
    return flg + sqn + cof + fgs


def calculate_fragments(type_of_input, data_size, file_or_msg):  # 1 1 test1.txt
    if type_of_input == 1:  # SPRAVA
        count_of_fragments = len(file_or_msg) / data_size
        if count_of_fragments > int(count_of_fragments):
            return int(count_of_fragments) + 1
        else:
            return int(count_of_fragments)
    elif type_of_input == 2:  # SUBOR
        size_of_file = os.path.getsize(file_or_msg)
        if size_of_file / data_size > int(size_of_file / data_size):
            return int(size_of_file / data_size) + 1
        else:
            return int(size_of_file / data_size)

def client_sends_msg(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, message):
    count_of_fragments = calculate_fragments(type_of_input, data_size, message)  # zistenie poctu posielanych fragmentov


def client_sends_file(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, file_name):
    count_of_attempts = 2
    count_of_name_fragments = calculate_fragments(1, data_size, file_name)  # type = 1 -> fragmentuje ako string
    count_of_file_fragments = calculate_fragments(type_of_input, data_size, file_name)  # zistenie poctu posielanych fragmentov
    print(count_of_name_fragments)
    print(count_of_file_fragments)

    header = create_header(2, 0, count_of_name_fragments, data_size)  # INF = 2, SQN = 0
    header_and_data = header + (2).to_bytes(1, 'big')  # HEADER + DATA
    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))  # Vypocitanie CRC z HEADER a DATA
    dat_message = crc16.to_bytes(2, 'big') + header_and_data  # Pridanie CRC pred hlavicku

    client_sock.sendto(dat_message, (server_ip, server_port))  # KLIENT posiela informacie (INF) SERVERU o pocte fragmentoch s nazvom suboru
    #t = Timer(0.5, timer)
    #t.start()
    data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
    parsed_data = parse_data(data)
    while parsed_data['flag'] == 3 and count_of_attempts > 0:
        header = create_header(2, parsed_data['sequence']+1, count_of_name_fragments, data_size)  # INF = 2, SQN = 0
        header_and_data = header + (2).to_bytes(1, 'big')  # HEADER + DATA
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))  # Vypocitanie CRC z HEADER a DATA
        dat_message = crc16.to_bytes(2, 'big') + header_and_data  # Pridanie CRC pred hlavicku
        client_sock.sendto(dat_message, (server_ip, server_port))
        data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
        parsed_data = parse_data(data)
        count_of_attempts -= 1




    # CLIENT posiela meno suboru aj s priponou
    if parsed_data['flag'] == 1:  # CLIENT prijima ACK spravu na INF spravu
        index = 1
        sent_fragments = []
        while index < count_of_name_fragments+1:  # 4 < 9   4 posiela 5.
            header = create_header(4, parsed_data['sequence'] + 1, count_of_name_fragments, data_size)  # DAT 3 9 1
            data_of_fragment = bytes(file_name[index-1:index-1+data_size], 'utf-8')  # t
            header_and_data = header + data_of_fragment
            sent_fragments.append(data_of_fragment)
            crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
            dat_message = crc16.to_bytes(2, 'big') + header_and_data

            client_sock.sendto(dat_message, (server_ip, server_port))  # 8. -> t

            if index % 5 == 0:  # index = 4  a posiela 5.
                data, server_ip_port = client_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)  # prijima ACK na posledne "t"
                if parsed_data['flag'] == 1:    # ACK
                    pass
                elif parsed_data['flag'] == 3:  # ERR
                    # TU SOM SOM SKONCIL - AK PRIDE ERR - NECYKLIT
                    print(sent_fragments)
                    print(parsed_data)
                    print(parsed_data['data'])
                    i = parsed_data['data_size']
                    j = 0
                    while j < i:
                        sequence = int.from_bytes(parsed_data['data'][j:j+3], 'big')
                        header = create_header(4, parsed_data['sequence'] + 1, count_of_name_fragments, data_size)  # DAT
                        data_of_fragment = sent_fragments[sequence-2]
                        header_and_data = header + data_of_fragment
                        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                        dat_message = crc16.to_bytes(2, 'big') + header_and_data

                        client_sock.sendto(dat_message, (server_ip, server_port))
                        print(sequence, sent_fragments[sequence-2])
                        j += 3


            else:
                parsed_data = parse_data(dat_message)
            index += 1  # 4


        # v parsed data mam ACK na posledne "t"
        # Nazov suboru je v tomto bode doposielany



    with open(file_name, "rb") as file:  # POSIELANIE DAT
        while True:
            byte = file.read(data_size)
            # header =
            if not byte:
                break
            client_sock.sendto(byte, (server_ip, server_port))
            data_from_server, server_ip_port = client_sock.recvfrom(fragment_size)  # + hlavicka + CRC
            print(data_from_server)

def client():
    # max velkost fragmentu je 1500 - 28 (IP + UDP header) - 9 (moja hlavicka) - 2 (CRC) = 1461
    data_size = 1         # int(input("Zadajte velkost dat v Bytoch: "))
    fragment_size = data_size + 11 + 15  # CLIENT moze prijat ERR packet, v ktorom bude 5 chybnych fragmentov so svojim sequence (kazdy ma 3 Byty)
    server_ip = "localhost"     # input("Zadajte cielovu IP adresu: ")
    server_port = 5005          # int(input("Zadajte cielovy port: "))
    print("1 -> Sprava")
    print("2 -> Subor")
    type_of_input = 2                    # int(input("Zadajte svoj vyber: "))

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    if type_of_input == 1:  # SPRAVA
        message = "Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS !"  # input
        client_sends_msg(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, message)
    elif type_of_input == 2:  # SUBOR
        file_name = "test1.txt"     # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
        client_sends_file(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, file_name)


def server():
    data_size = 1         # int(input("Zadajte velkost dat v Bytoch: "))
    fragment_size = data_size + 11  # velkost hlavicky = 9, velkost CRC = 2
    server_ip = "localhost"     # input("Zadajte IP adresu: ")
    server_port = 5005          # int(input("Zadajte port: "))

    count_of_attempts = 2
    type_of_input = 0
    sequence = 0
    count_of_fragments = 0

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((server_ip, server_port))
    data, client_ip_port = server_sock.recvfrom(fragment_size)  # SERVER ocakava INF

    parsed_data = parse_data(data)

    result = check_crc(data)
    while result == 0 and count_of_attempts > 0:  # INF sprava neprisla spravne, prebiehaju 3 pokusy o znovuposlanie INF spravy
        print("Informacna sprava neprisla spravne")
        print("Pocet zostavajucich pokusov: ", count_of_attempts)
        header = create_header(3, parsed_data['sequence']+1, 0, 3)  # ERR = 3, SQN = 1, COUNT_OF_FRAGMENTS = 1, DATA_SIZE = 3
        header_and_data = header + parsed_data['sequence'].to_bytes(3, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        inf_message = crc16.to_bytes(2, 'big') + header_and_data
        server_sock.sendto(inf_message, client_ip_port)
        data, client_ip_port = server_sock.recvfrom(fragment_size)
        parsed_data = parse_data(data)
        result = check_crc(data)
        count_of_attempts -= 1
    if result == 0 and count_of_attempts == 0:
        server_sock.close()
        print("Informacna sprava po 3 pokusoch neprisla spravne")
    elif result == 1:  # Prva informacna sprava prisla v poriadku
        if parsed_data['flag'] == 2:
            type_of_input = int.from_bytes(parsed_data['data'], 'big')  # 2
            sequence = parsed_data['sequence']                          # 0
            count_of_fragments = parsed_data['count_of_fragments']      # 9
            header = create_header(1, parsed_data['sequence'] + 1, 0, 0)
            crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
            inf_message = crc16.to_bytes(2, 'big') + header
            server_sock.sendto(inf_message, client_ip_port)  # SERVER posiela ACK
        if type_of_input == 2:  # SUBOR
            # SERVER prijima data o nazve suboru




            index = 1
            heap_file_name = []
            heapq.heapify(heap_file_name)
            error_results = []
            while index < count_of_fragments+1:  # 4 < 9   4 caka na 5.
                data, client_ip_port = server_sock.recvfrom(fragment_size)  # 5.
                parsed_data = parse_data(data)
                result = check_crc(data)
                if result == 0:  # chybny fragment
                    error_results.append(parsed_data['sequence'])  # error_results[2]
                    print(parsed_data)
                    print(error_results)
                elif result == 1:
                    heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))  # 2 "t"

                if index % 5 == 0:
                    if len(error_results) > 0:
                        header = create_header(3, parsed_data['sequence'] + 1, len(error_results), len(error_results)*3)  # ERR
                        data_of_fragment = bytes()
                        for fragment in error_results:
                            data_of_fragment += fragment.to_bytes(3, 'big')
                        header_and_data = header + data_of_fragment
                        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                        err_message = crc16.to_bytes(2, 'big') + header_and_data
                        print("ERRORS - ", error_results)
                        print("HEAP - ", heap_file_name)
                        server_sock.sendto(err_message, client_ip_port)
                        """i = 0  ZLE - ZACYKLUJEM SA
                        while i < len(error_results):
                            data, client_ip_port = server_sock.recvfrom(fragment_size)
                            parsed_data = parse_data(data)
                            heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))
                            i += 1"""
                    elif len(error_results) == 0:
                        header = create_header(1, parsed_data['sequence'] + 1, 0, 0)  # ACK
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        inf_message = crc16.to_bytes(2, 'big') + header
                        server_sock.sendto(inf_message, client_ip_port)
                index += 1  # 4



            file_name = ""
            while heap_file_name:
                file_name += heapq.heappop(heap_file_name)[1]
            print(file_name)
            print("Uz nepocuvam")


    # {'crc': 51641, 'flag': 2, 'sequence': 0, 'count_of_fragments': 9, 'data_size': 1, 'data': b'\x02'}





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

"""parsed_data = {'flg': int(data.hex()[6:8], 16), 'sqn': int(data.hex()[14:16], 16)}
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
    parsed_data['fnm'] = bytes.fromhex(file_name).decode("ASCII")"""