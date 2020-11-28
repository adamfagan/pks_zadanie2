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

ACK = 1
INF = 2
ERR = 3
DAT = 4
SIZE_OF_HEADER = 9
SIZE_OF_CRC = 2

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
    count_of_name_fragments = calculate_fragments(1, data_size, file_name)  # type = 1 -> fragmentuje ako string
    count_of_file_fragments = calculate_fragments(type_of_input, data_size, file_name)  # zistenie poctu posielanych fragmentov

    # ZACIATOK KOMUNIKACIE
    # CLIENT POSIELA FRAGMENTY S MENOM SUBORU
    # VYTVARANIE INF FRAGMENTU
    header = create_header(INF, 0, count_of_name_fragments, data_size)
    header_and_data = header + (2).to_bytes(1, 'big')
    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
    inf_message = crc16.to_bytes(2, 'big') + header_and_data
    # KONIEC VYTVARANIA INF FRAGMENTU
    # ODOSLANIE INF FRAGMENTU SERVERU
    client_sock.sendto(inf_message, (server_ip, server_port))
    #t = Timer(0.5, timer)
    #t.start()
    # CLIENT OCAKAVA ACK FRAGMENT OD SERVERA
    data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
    parsed_data = parse_data(data)
    count_of_attempts = 2
    # AK INF FRAGMENT PRISIEL NA SERVER POSKODENY, TAK CLIENT SKUSA POSLAT INF FRAGMENT ESTE 2-KRAT
    while parsed_data['flag'] == ERR and count_of_attempts > 0:
        # VYTVARANIE INF FRAGMENTU
        header = create_header(INF, parsed_data['sequence']+1, count_of_name_fragments, data_size)  # INF = 2, SQN = 0
        header_and_data = header + (2).to_bytes(1, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        inf_message = crc16.to_bytes(2, 'big') + header_and_data
        # KONIEC VYTVARANIA INF FRAGMENTU
        # ODOSLANIE INF FRAGMENTU SERVERU
        client_sock.sendto(inf_message, (server_ip, server_port))
        # CLIENT OCAKAVA ACK FRAGMENT OD SERVERA
        data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
        parsed_data = parse_data(data)
        count_of_attempts -= 1

    # CLIENT POSIELA DAT FRAGMENTY S MENOM SUBORU
    if parsed_data['flag'] == ACK:
        sent_fragments = []  # POLE S ODOSLANYCH FRAGMENTOV JEDNEHO BLOKU
        index = 1
        while index < count_of_name_fragments+1:  # 1 < 10
            # CLIENT POSIELA SERVERU "count_of_fragments" DAT FRAGMENTOV
            # VYTVARANIE DAT FRAGMENTU
            header = create_header(DAT, parsed_data['sequence']+1, count_of_name_fragments, data_size)
            data_of_fragment = bytes(file_name[index-1:index-1+data_size], 'utf-8')
            header_and_data = header + data_of_fragment
            crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
            dat_message = crc16.to_bytes(2, 'big') + header_and_data
            # KONIEC VYTVARANIA DAT FRAGMENTU
            # ODOSLANIE DAT FRAGMENTU SERVERU
            client_sock.sendto(dat_message, (server_ip, server_port))

            # ULOZENIE SI PRAVE ODOSLANEHO DAT FRAGMENTU
            sent_fragments.append(data_of_fragment)




            # PRIJIMANIE ACK ALEBO ERR FRAGMENTU PO ODOSLANI KAZDYCH 5 FRAGMENTOV
            if index % 5 == 0:
                # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
                data, server_ip_port = client_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)
                if parsed_data['flag'] == ACK:
                    pass




                elif parsed_data['flag'] == ERR:


                    """i = 0
                    while i < parsed_data['data_size']:
                        sequence = int.from_bytes(parsed_data['data'][i:i+3], 'big')
                        # VYTVARANIE DAT FRAGMENTU
                        header = create_header(DAT, parsed_data['sequence']+1, count_of_name_fragments, data_size)
                        # VYBRANIE DAT URCITEHO ZLE ODOSLANEHO FRAGMENTU
                        data_of_fragment = sent_fragments[sequence-2]
                        header_and_data = header + data_of_fragment
                        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                        dat_message = crc16.to_bytes(2, 'big') + header_and_data
                        # KONIEC VYTVARANIA DAT FRAGMENTU
                        # ODOSLANIE DAT FRAGMENTU SERVERU
                        client_sock.sendto(dat_message, (server_ip, server_port))

                        i += 3"""




            else:
                parsed_data = parse_data(dat_message)
            index += 1

    elif parsed_data['flag'] == ERR:
        client_sock.close()
        print("INF fragment sa po 3 pokusoch nepodarilo dorucit")

    # POSIELANIE DAT
    with open(file_name, "rb") as file:
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
    data_size = 1               # int(input("Zadajte velkost dat v Bytoch: "))
    fragment_size = data_size + SIZE_OF_HEADER + SIZE_OF_CRC
    server_ip = "localhost"     # input("Zadajte IP adresu: ")
    server_port = 5005          # int(input("Zadajte port: "))

    type_of_input = 0
    sequence = 0
    count_of_fragments = 0

    # SERVER ZACINA POCUVAT NA "server_sock"
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_sock.bind((server_ip, server_port))
    # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
    data, client_ip_port = server_sock.recvfrom(fragment_size)

    # PARSOVANIE INF FRAGMENTU
    parsed_data = parse_data(data)

    # KONTROLA CI PRISIEL INF FRAGMENT SPRAVNE
    result = check_crc(data)

    count_of_attempts = 2
    # INF FRAGMENT NEPRISIEL SPRAVNE A SERVER SI ZIADA POSLAT INF FRAGMENT ESTE 2-KRAT
    while result == 0 and count_of_attempts > 0:  # INF sprava neprisla spravne, prebiehaju 3 pokusy o znovuposlanie INF spravy
        print("Informacny fragment neprisiel spravne")
        print("Pocet zostavajucich pokusov: ", count_of_attempts)

        # VYTVARANIE ERR FRAGMENTU
        header = create_header(ERR, parsed_data['sequence']+1, 0, 3)
        header_and_data = header + parsed_data['sequence'].to_bytes(3, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        err_message = crc16.to_bytes(2, 'big') + header_and_data
        # KONIEC VYTVARANIA ERR FRAGMENTU
        # ODOSLANIE ERR FRAGMENTU CLIENTOVI
        server_sock.sendto(err_message, client_ip_port)
        # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
        data, client_ip_port = server_sock.recvfrom(fragment_size)
        # PARSOVANIE INF FRAGMENTU
        parsed_data = parse_data(data)
        result = check_crc(data)
        count_of_attempts -= 1
    # INF FRAGMENT NEPRISIEL OD CLIENTA 3-KRAT SPRAVNE A SERVER UZATVARA SVOJ SOCKET
    if result == 0 and count_of_attempts == 0:
        server_sock.close()
        print("Informacny fragment po 3 pokusoch neprisiel spravne")
    # INF FRAGMENT PRISIEL SPRAVNE
    elif result == 1:
        if parsed_data['flag'] == INF:
            type_of_input = int.from_bytes(parsed_data['data'], 'big')  # SPRAVA ALEBO SUBOR
            count_of_fragments = parsed_data['count_of_fragments']
            # VYTVARANIE ACK FRAGMENTU NA ODPOVEDANIE CLIENTOVI, ZE INF FRAGMENT PRISIEL SPAVNE
            header = create_header(ACK, parsed_data['sequence']+1, 0, 0)
            crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
            ack_message = crc16.to_bytes(2, 'big') + header
            # KONIEC VYTVARANIA ACK FRAGMENTU
            # ODOSLANIE ACK FRAGMENTU CLIENTOVI
            server_sock.sendto(ack_message, client_ip_port)  # SERVER posiela ACK
        if type_of_input == 2:  # SUBOR
            # SERVER PRIJIMA DAT FRAGMENTI O MENE SUBORU
            heap_file_name = []  # BINARNA HALDA NA UKLADANIE MENA SUBORU
            heapq.heapify(heap_file_name)
            error_results = []  # POLE NA UKLADANIE CHYBNYCH FRAGMENTOV
            index = 1




            while index < count_of_fragments+1:  # 1 < 10
                # SERVER PRIJIMA OD CLIENTA "count_of_fragments" DAT FRAGMENTOV
                data, client_ip_port = server_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)
                result = check_crc(data)
                # SERVER PRIJAL CHYBNY FRAGMENT
                if result == 0:
                    # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV
                    error_results.append(parsed_data['sequence'])
                # SERVER PRIJAL NEPOSKODENY FRAGMENT
                elif result == 1:
                    # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                    heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))  # 2 "t"
                # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                if index % 5 == 0:
                    # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA CLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
                    if len(error_results) > 0:
                        # VYTVARANIE ERR FRAGMENTU
                        header = create_header(ERR, parsed_data['sequence']+1, len(error_results), len(error_results)*3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                        data_of_fragment = bytes()
                        for fragment in error_results:
                            data_of_fragment += fragment.to_bytes(3, 'big')
                        header_and_data = header + data_of_fragment
                        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                        err_message = crc16.to_bytes(2, 'big') + header_and_data
                        # KONIEC VYTVARANIA ERR FRAGMENTU
                        # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                        server_sock.sendto(err_message, client_ip_port)
                        """i = 0  ZLE - ZACYKLUJEM SA
                        while i < len(error_results):
                            data, client_ip_port = server_sock.recvfrom(fragment_size)
                            parsed_data = parse_data(data)
                            heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))
                            i += 1"""
                    # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                    elif len(error_results) == 0:
                        # VYTVARANIE ACK FRAGMENTU
                        header = create_header(ACK, parsed_data['sequence']+1, 0, 0)  # ACK
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        ack_message = crc16.to_bytes(2, 'big') + header
                        # KONIEC VYTVARANIA ACK FRAGMENTU
                        # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                        server_sock.sendto(ack_message, client_ip_port)
                index += 1  # 4
            # SKLADANIE MENO SUBORU Z BINARNEJ HALDY
            file_name = ""
            while heap_file_name:
                file_name += heapq.heappop(heap_file_name)[1]
            print(file_name)
        elif type_of_input == 1:  # SPRAVA
            pass




    header = create_header(ACK, parsed_data["sqn"] + 1, 0, 0)  # 5 odstranit a nahradit uz parsnutimi datami
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