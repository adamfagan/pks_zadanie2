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
SAG = 5
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
    #new_crc = GetCrc16(str(int.from_bytes(data[2:], 'big')))
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


def inf_send2(parsed_data, client_sock, server_ip, server_port, fragment_size, count_of_name_fragments, data_size):
    count_of_attempts = 2
    sequence_num = 2
    while parsed_data['flag'] == ERR and count_of_attempts > 0:  # 1 > 0
        # VYTVARANIE INF FRAGMENTU
        header = create_header(INF, sequence_num, count_of_name_fragments, data_size)
        header_and_data = header + (2).to_bytes(1, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        inf_message = crc16.to_bytes(2, 'big') + header_and_data
        # KONIEC VYTVARANIA INF FRAGMENTU

        # ODOSLANIE INF FRAGMENTU NA SERVER
        client_sock.sendto(inf_message, (server_ip, server_port))

        # CLIENT OCAKAVA ACK FRAGMENT OD SERVERA
        data, server_ip_port = client_sock.recvfrom(fragment_size)  # TU
        parsed_data = parse_data(data)
        count_of_attempts -= 1  # 0
        sequence_num += 2
    return sequence_num, parsed_data


def client_sends_file(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, file_name):
    count_of_name_fragments = calculate_fragments(1, data_size, file_name)  # type = 1 -> fragmentuje ako string
    count_of_file_fragments = calculate_fragments(type_of_input, data_size, file_name)  # zistenie poctu posielanych fragmentov
    sequence_num = 2

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

    # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
    data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
    parsed_data = parse_data(data)

    # AK INF FRAGMENT PRISIEL NA SERVER POSKODENY, TAK CLIENT SKUSA POSLAT INF FRAGMENT ESTE 2-KRAT
    if parsed_data['flag'] == ERR:
        sequence_num, parsed_data = inf_send2(parsed_data, client_sock, server_ip, server_port, fragment_size, count_of_name_fragments, data_size)

    # AK INF PRISIEL NA SERVER SPRAVNE, TAK CLIENT POSIELA FRAGMENTY
    if parsed_data['flag'] == ACK:
        sent_fragments = {}  # DICITONARY ODOSLANYCH FRAGMENTOV
        index = 0
        correctly_sent_fragments = 0
        already_sent_fragments = 0
        switcher = 0

        # ZACIATOK PRVEJ KOMUNIKACIE
        # CLIENT POSIELA FRAGMENTY S MENOM SUBORU
        while correctly_sent_fragments != count_of_name_fragments:
            if switcher == 1:
                i = 0
                while i < parsed_data['data_size']:
                    sequence = int.from_bytes(parsed_data['data'][i:i+3], 'big')
                    # VYTVARANIE DAT FRAGMENTU
                    header = create_header(SAG, sequence_num, count_of_name_fragments, data_size)
                    # VYBRANIE DAT URCITEHO ZLE ODOSLANEHO FRAGMENTU
                    data_of_fragment = sent_fragments.get(sequence)
                    header_and_data = header + data_of_fragment
                    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                    dat_message = crc16.to_bytes(2, 'big') + header_and_data
                    # KONIEC VYTVARANIA DAT FRAGMENTU
                    # ODOSLANIE DAT FRAGMENTU SERVERU
                    client_sock.sendto(dat_message, (server_ip, server_port))
                    already_sent_fragments += 1
                    sent_fragments[sequence_num] = data_of_fragment
                    sequence_num += 1
                    i += 3
                switcher = 0
            # CLIENT POSIELA SERVERU "count_of_fragments" DAT FRAGMENTOV
            if index < count_of_name_fragments:
                # VYTVARANIE DAT FRAGMENTU
                header = create_header(DAT, sequence_num, count_of_name_fragments, data_size)
                data_of_fragment = bytes(file_name[index:index+data_size], 'utf-8')
                header_and_data = header + data_of_fragment
                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                dat_message = crc16.to_bytes(2, 'big') + header_and_data
                # KONIEC VYTVARANIA DAT FRAGMENTU
                # ODOSLANIE DAT FRAGMENTU SERVERU
                client_sock.sendto(dat_message, (server_ip, server_port))
                already_sent_fragments += 1
                sent_fragments[sequence_num] = data_of_fragment
                # ULOZENIE SI PRAVE ODOSLANEHO DAT FRAGMENTU
                sequence_num += 1
            # PRIJIMANIE ACK ALEBO ERR FRAGMENTU PO ODOSLANI KAZDYCH 5 FRAGMENTOV
            if already_sent_fragments == 5 or (index >= count_of_name_fragments):
                # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
                data, server_ip_port = client_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)
                if parsed_data['flag'] == ACK:
                    correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                elif parsed_data['flag'] == ERR:
                    correctly_sent_fragments = correctly_sent_fragments + (already_sent_fragments - parsed_data['count_of_fragments'])  # correctly_sent_fragments = 6
                    switcher = 1
                already_sent_fragments = 0
                sequence_num += 1
            # ACK ALEBO ERR FRAGMENT PRISIEL NESPRAVNE

            index += 1
        sent_fragments.clear()


        # ZACIATOK DRUHEJ KOMUNIKACIE
        # CLIENT POSIELA FRAGMENTY DAT SUBORU
        # VYTVARANIE INF FRAGMENTU
        header = create_header(INF, 0, count_of_file_fragments, data_size)
        header_and_data = header + (2).to_bytes(1, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        inf_message = crc16.to_bytes(2, 'big') + header_and_data
        # KONIEC VYTVARANIA INF FRAGMENTU
        # ODOSLANIE INF FRAGMENTU SERVERU
        client_sock.sendto(inf_message, (server_ip, server_port))
        # t = Timer(0.5, timer)
        # t.start()
        # CLIENT OCAKAVA ACK FRAGMENT OD SERVERA
        data, server_ip_port = client_sock.recvfrom(fragment_size)  # dostavam ACK na INF
        parsed_data = parse_data(data)
        count_of_attempts = 2
        sequence_num = 2
        # AK INF FRAGMENT PRISIEL NA SERVER POSKODENY, TAK CLIENT SKUSA POSLAT INF FRAGMENT ESTE 2-KRAT
        while parsed_data['flag'] == ERR and count_of_attempts > 0:
            # VYTVARANIE INF FRAGMENTU
            header = create_header(INF, parsed_data['sequence'] + 1, count_of_file_fragments, data_size)  # INF = 2, SQN = 0
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
            sequence_num += 2
            # CLIENT POSIELA FRAGMENTY
        if parsed_data['flag'] == ACK:
            sent_fragments = {}  # DICITONARY ODOSLANYCH FRAGMENTOV JEDNEHO BLOKU
            correctly_sent_fragments = 0
            switcher = 0
            already_sent_fragments = 0
            # CLIENT POSIELA FRAGMENTY S MENOM SUBORU
            with open(file_name, "rb") as file:
                not_byte = 1
                while correctly_sent_fragments != count_of_file_fragments:
                    if switcher == 1:
                        i = 0
                        while i < parsed_data['data_size']:
                            sequence = int.from_bytes(parsed_data['data'][i:i + 3], 'big')
                            # VYTVARANIE SAG FRAGMENTU
                            header = create_header(SAG, sequence_num, count_of_file_fragments, data_size)
                            # VYBRANIE SAG URCITEHO ZLE ODOSLANEHO FRAGMENTU
                            data_of_fragment = sent_fragments.get(sequence)
                            header_and_data = header + data_of_fragment
                            crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                            dat_message = crc16.to_bytes(2, 'big') + header_and_data
                            # KONIEC VYTVARANIA SAG FRAGMENTU
                            # ODOSLANIE SAG FRAGMENTU SERVERU
                            client_sock.sendto(dat_message, (server_ip, server_port))
                            already_sent_fragments += 1
                            sent_fragments[sequence_num] = data_of_fragment
                            sequence_num += 1
                            i += 3
                        switcher = 0
                    while already_sent_fragments != 5 and not_byte == 1:
                        byte = file.read(data_size)
                        if not byte:
                            not_byte = 0
                            break
                        # VYTVARANIE DAT FRAGMENTU
                        header = create_header(DAT, sequence_num, count_of_file_fragments, data_size)
                        data_of_fragment = byte
                        header_and_data = header + data_of_fragment
                        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                        dat_message = crc16.to_bytes(2, 'big') + header_and_data
                        # KONIEC VYTVARANIA DAT FRAGMENTU
                        # ODOSLANIE DAT FRAGMENTU SERVERU
                        client_sock.sendto(dat_message, (server_ip, server_port))
                        already_sent_fragments += 1
                        sent_fragments[sequence_num] = data_of_fragment
                        # ULOZENIE SI PRAVE ODOSLANEHO DAT FRAGMENTU
                        sequence_num += 1
                    if (already_sent_fragments == 5) or (not_byte == 0):
                        # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
                        data, server_ip_port = client_sock.recvfrom(fragment_size)
                        parsed_data = parse_data(data)
                        if parsed_data['flag'] == ACK:
                            correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                        elif parsed_data['flag'] == ERR:
                            correctly_sent_fragments = correctly_sent_fragments + (already_sent_fragments - parsed_data['count_of_fragments'])  # correctly_sent_fragments = 6
                            switcher = 1
                        already_sent_fragments = 0
                        sequence_num += 1
        elif parsed_data['flag'] == ERR and count_of_attempts == 0:
            client_sock.close()
            print("INF fragment sa po 3 pokusoch nepodarilo dorucit")
    elif parsed_data['flag'] == ERR:
        client_sock.close()
        print("INF fragment sa po 3 pokusoch nepodarilo dorucit")


def client():
    # max velkost fragmentu je 1500 - 28 (IP + UDP header) - 9 (moja hlavicka) - 2 (CRC) = 1461
    data_size = 1         # int(input("Zadajte velkost dat v Bytoch: "))
    fragment_size = data_size + SIZE_OF_HEADER + SIZE_OF_CRC + 15  # CLIENT moze prijat ERR packet, v ktorom bude 5 chybnych fragmentov so svojim sequence (kazdy ma 3 Byty)
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

def inf_receive2(result, parsed_data, server_sock, client_ip_port, fragment_size):
    count_of_attempts = 2
    # INF FRAGMENT NEPRISIEL SPRAVNE A SERVER SI ZIADA POSLAT INF FRAGMENT ESTE 2-KRAT
    while result == 0 and count_of_attempts > 0:  # 0 > 0
        print("Informacny fragment neprisiel spravne")
        print("Pocet zostavajucich pokusov: ", count_of_attempts)  # 1

        # VYTVARANIE ERR FRAGMENTU
        header = create_header(ERR, parsed_data['sequence']+1, 0, 0)
        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
        err_message = crc16.to_bytes(2, 'big') + header
        # KONIEC VYTVARANIA ERR FRAGMENTU

        # ODOSLANIE ERR FRAGMENTU CLIENTOVI
        server_sock.sendto(err_message, client_ip_port)

        # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
        data, client_ip_port = server_sock.recvfrom(fragment_size)  # TU

        # PARSOVANIE INF FRAGMENTU
        parsed_data = parse_data(data)
        result = check_crc(data)
        count_of_attempts -= 1  # 0

    # INF FRAGMENT PRISIEL OD CLIENTA 3-KRAT NESPRAVNE A SERVER UZATVARA SVOJ SOCKET
    if result == 0 and count_of_attempts == 0:
        header = create_header(ERR, parsed_data['sequence'] + 1, 0, 0)
        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
        err_message = crc16.to_bytes(2, 'big') + header
        server_sock.sendto(err_message, client_ip_port)
        return result, parsed_data
    elif result == 1 and count_of_attempts >= 0:
        return result, parsed_data

def server():
    data_size = 1               # int(input("Zadajte velkost dat v Bytoch: "))
    fragment_size = data_size + SIZE_OF_HEADER + SIZE_OF_CRC
    server_ip = "localhost"     # input("Zadajte IP adresu: ")
    server_port = 5005          # int(input("Zadajte port: "))
    path = 'C:/Users/adamf/Desktop/PKS_files'

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

    # INF FRAGMENT PRISIEL NESPRAVNE
    if result == 0:
        result, parsed_data = inf_receive2(result, parsed_data, server_sock, client_ip_port, fragment_size)

    # INF FRAGMENT PRISIEL SPRAVNE
    if result == 1:
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
            error_results_heap = []
            index = 1
            sag_flags = 0
            count_of_accepted_fragments = 1
            while len(heap_file_name) != count_of_fragments:
                # SERVER PRIJIMA OD CLIENTA "count_of_fragments" DAT FRAGMENTOV
                data, client_ip_port = server_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)

                # SERVER PRIJAL DAT FRAGMENT
                if parsed_data['flag'] == DAT:
                    result = check_crc(data)
                    # SERVER PRIJAL CHYBNY FRAGMENT
                    if result == 0:
                        # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV
                        error_results.append(parsed_data['sequence'])
                        error_results_heap.append(parsed_data['sequence'])
                    # SERVER PRIJAL NEPOSKODENY FRAGMENT
                    elif result == 1:
                        # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                        # heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))
                        heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data']))
                        print("spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                        count_of_accepted_fragments += 1

                # SERVER PRIJAL SAG FRAGMENT
                elif parsed_data['flag'] == SAG:
                    result = check_crc(data)
                    # SERVER PRIJAL CHYBNY FRAGMENT
                    if result == 0:
                        error_results.append(parsed_data['sequence'])
                    elif result == 1:
                        # heapq.heappush(heap_file_name, (error_results_heap[sag_flags], parsed_data['data'].decode('utf-8')))
                        heapq.heappush(heap_file_name, (error_results_heap[sag_flags], parsed_data['data']))
                        print("spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                        count_of_accepted_fragments += 1
                        error_results_heap.pop(sag_flags)
                        sag_flags -= 1
                    sag_flags += 1

                # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                if index == 5 or (len(error_results) + len(heap_file_name) == count_of_fragments):
                    sag_flags = 0
                    index = 0
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
                        error_results.clear()
                    # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                    elif len(error_results) == 0:
                        # VYTVARANIE ACK FRAGMENTU
                        header = create_header(ACK, parsed_data['sequence']+1, 0, 0)
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        ack_message = crc16.to_bytes(2, 'big') + header
                        # KONIEC VYTVARANIA ACK FRAGMENTU
                        # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                        server_sock.sendto(ack_message, client_ip_port)
                index += 1

            # SKLADANIE MENA SUBORU Z BINARNEJ HALDY
            file_name = ""
            while heap_file_name:
                file_name += heapq.heappop(heap_file_name)[1].decode('utf-8')
            print(file_name)



            # DRUHA KOMUNIKACIA
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
                print("Informacny fragment po 3 pokusoch neprisiel spravne")
                header = create_header(ERR, parsed_data['sequence']+1, 0, 3)
                header_and_data = header + parsed_data['sequence'].to_bytes(3, 'big')
                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                err_message = crc16.to_bytes(2, 'big') + header_and_data
                server_sock.sendto(err_message, client_ip_port)
                server_sock.close()
            # INF FRAGMENT PRISIEL SPRAVNE
            elif result == 1:
                if parsed_data['flag'] == INF:
                    count_of_file_fragments = parsed_data['count_of_fragments']
                    # VYTVARANIE ACK FRAGMENTU NA ODPOVEDANIE CLIENTOVI, ZE INF FRAGMENT PRISIEL SPAVNE
                    header = create_header(ACK, parsed_data['sequence']+1, 0, 0)
                    crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                    ack_message = crc16.to_bytes(2, 'big') + header
                    # KONIEC VYTVARANIA ACK FRAGMENTU
                    # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                    server_sock.sendto(ack_message, client_ip_port)  # SERVER posiela ACK
                    heap_file_name.clear()
                    heapq.heapify(heap_file_name)
                    error_results.clear()  # POLE NA UKLADANIE CHYBNYCH FRAGMENTOV
                    error_results_heap.clear()
                    index = 1
                    sag_flags = 0
                    while len(heap_file_name) != count_of_file_fragments:
                        # SERVER PRIJIMA OD CLIENTA "count_of_file_fragments" DAT FRAGMENTOV
                        data, client_ip_port = server_sock.recvfrom(fragment_size)
                        parsed_data = parse_data(data)

                        # SERVER PRIJAL DAT FRAGMENT
                        if parsed_data['flag'] == DAT:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY FRAGMENT
                            if result == 0:
                                # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV
                                error_results.append(parsed_data['sequence'])
                                error_results_heap.append(parsed_data['sequence'])
                            # SERVER PRIJAL NEPOSKODENY FRAGMENT
                            elif result == 1:
                                # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                                heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data']))
                                print("spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                                count_of_accepted_fragments += 1

                        # SERVER PRIJAL SAG FRAGMENT
                        elif parsed_data['flag'] == SAG:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY FRAGMENT
                            if result == 0:
                                error_results.append(parsed_data['sequence'])
                            elif result == 1:
                                heapq.heappush(heap_file_name, (error_results_heap[sag_flags], parsed_data['data']))
                                print("spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                                count_of_accepted_fragments += 1
                                error_results_heap.pop(sag_flags)
                                sag_flags -= 1
                            sag_flags += 1

                        # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                        if index == 5 or (len(error_results) + len(heap_file_name) == count_of_file_fragments):
                            sag_flags = 0
                            index = 0
                            # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA CLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
                            if len(error_results) > 0:
                                # VYTVARANIE ERR FRAGMENTU
                                header = create_header(ERR, parsed_data['sequence'] + 1, len(error_results), len(error_results) * 3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                                data_of_fragment = bytes()
                                for fragment in error_results:
                                    data_of_fragment += fragment.to_bytes(3, 'big')
                                header_and_data = header + data_of_fragment
                                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                                err_message = crc16.to_bytes(2, 'big') + header_and_data
                                # KONIEC VYTVARANIA ERR FRAGMENTU
                                # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                                server_sock.sendto(err_message, client_ip_port)
                                error_results.clear()
                            # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                            elif len(error_results) == 0:
                                # VYTVARANIE ACK FRAGMENTU
                                header = create_header(ACK, parsed_data['sequence'] + 1, 0, 0)  # ACK
                                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                ack_message = crc16.to_bytes(2, 'big') + header
                                # KONIEC VYTVARANIA ACK FRAGMENTU
                                # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                                server_sock.sendto(ack_message, client_ip_port)
                        index += 1  # 3
                    # SKLADANIE MENA SUBORU Z BINARNEJ HALDY
                    print("ZACINAM VKLADAT DATA DO SUBORU")
                    with open(os.path.join(path, file_name), 'wb') as fp:
                        while heap_file_name:
                            fp.write(heapq.heappop(heap_file_name)[1])
                    print("Dokoncene")
        elif type_of_input == 1:  # SPRAVA
            pass
    elif result == 0:
        server_sock.close()
        print("Informacny fragment po 3 pokusoch neprisiel spravne")


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

# POSIELANIE DAT
"""with open(file_name, "rb") as file:
    while True:
        byte = file.read(data_size)
        if not byte:
            break
        client_sock.sendto(byte, (server_ip, server_port))
        data_from_server, server_ip_port = client_sock.recvfrom(fragment_size)  # + hlavicka + CRC
        print(data_from_server)"""

#t = Timer(0.5, timer)
    #t.start()


"""count_of_attempts = 2
                    # INF FRAGMENT NEPRISIEL SPRAVNE A SERVER SI ZIADA POSLAT INF FRAGMENT ESTE 2-KRAT
                    while result == 0 and count_of_attempts > 0:  # INF sprava neprisla spravne, prebiehaju 3 pokusy o znovuposlanie INF spravy
                        print("ACK alebo ERR fragment neprisiel spravne")  # 0 > 0
                        print("Pocet zostavajucich pokusov: ", count_of_attempts)

                        # VYTVARANIE ERR FRAGMENTU
                        header = create_header(ERR, sequence_num, 0, 0)
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        err_message = crc16.to_bytes(2, 'big') + header
                        # KONIEC VYTVARANIA ERR FRAGMENTU
                        # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                        client_sock.sendto(err_message, (server_ip, server_port))
                        # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
                        data, server_ip_port = client_sock.recvfrom(fragment_size)
                        # PARSOVANIE INF FRAGMENTU
                        parsed_data = parse_data(data)
                        result = check_crc(data)
                        sequence_num += 1
                        count_of_attempts -= 1  # 0
                    # ACK ALEBO ERR FRAGMENT NEPRISIEL OD SERVERA 3-KRAT SPRAVNE A CLIENT UZATVARA SVOJ SOCKET
                    if result == 0 and count_of_attempts == 0:
                        print("ACK alebo ERR fragment po 3 pokusoch neprisiel spravne")
                        header = create_header(ERR, sequence_num, 0, 0)
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        err_message = crc16.to_bytes(2, 'big') + header
                        client_sock.sendto(err_message, (server_ip, server_port))
                        ack_err_accepted = 0
                        client_sock.close()"""

"""# SERVER PRIJAL ERR FRAGMENT
                elif parsed_data['flag'] == ERR:
                    count_of_attempts = 2
                    if len(last_data) == 1:
                        while parsed_data['flag'] == ERR and count_of_attempts > 0:
                            # VYTVORENIE ACK FRAGMENTU
                            header = create_header(ACK, parsed_data['sequence'] + 1, 0, 0)
                            crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                            ack_message = crc16.to_bytes(2, 'big') + header
                            # KONIEC VYTVARANIA ACK FRAGMENTU
                            # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                            server_sock.sendto(ack_message, client_ip_port)
                            # SERVER OCAKAVA DAT, SAG, ALEBO ERR FRAGMENT OD CLIENTA
                            data, client_ip_port = server_sock.recvfrom(fragment_size)
                            # PARSOVANIE DAT, SAG, ALEBO ERR FRAGMENTU
                            parsed_data = parse_data(data)
                            count_of_attempts -= 1
                        if parsed_data['flag'] == ERR and count_of_attempts == 0:
                            print("ACK alebo ERR fragment sa po 3 pokusoch nepodarilo dorucit")
                            ack_err_accepted = 0
                            server_sock.close()
                    else:
                        while parsed_data['flag'] == ERR and count_of_attempts > 0:  # 0 > 0
                            # VYTVARANIE ERR FRAGMENTU
                            header = create_header(ERR, parsed_data['sequence']+1, len(error_results), len(error_results) * 3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                            header_and_data = header + last_data
                            crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                            err_message = crc16.to_bytes(2, 'big') + header_and_data
                            # KONIEC VYTVARANIA ERR FRAGMENTU
                            # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                            server_sock.sendto(err_message, client_ip_port)  # posiela 3. krat
                            # SERVER OCAKAVA DAT, SAG, ALEBO ERR FRAGMENT OD CLIENTA
                            data, client_ip_port = server_sock.recvfrom(fragment_size)
                            # PARSOVANIE DAT, SAG, ALEBO ERR FRAGMENTU
                            parsed_data = parse_data(data)
                            count_of_attempts -= 1  # 0
                        if parsed_data['flag'] == ERR and count_of_attempts == 0:
                            print("ACK alebo ERR fragment sa po 3 pokusoch nepodarilo dorucit")
                            ack_err_accepted = 0
                            server_sock.close()"""