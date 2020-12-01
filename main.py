# ------------------------------------------
# -- FLAG - SEQUENCE -     DATA     - CRC --
# ------------------------------------------
# from tkinter import *
import socket
import os
import heapq
import time
import threading
from random import randint

from crc16 import GetCrc16

ACK = 1
INF = 2
ERR = 3
DAT = 4
SAG = 5
KPA = 6
SIZE_OF_HEADER = 9
SIZE_OF_CRC = 2


def check_crc(data):
    original_crc = int.from_bytes(data[0:2], 'big')
    if randint(0, 100) > 100:
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
    data, server_ip_port = client_sock.recvfrom(fragment_size)
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
        errors = 0
        # ZACIATOK PRVEJ KOMUNIKACIE
        # CLIENT POSIELA FRAGMENTY S MENOM SUBORU
        while correctly_sent_fragments != count_of_name_fragments and errors == 0:
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
                try:
                    client_sock.settimeout(0.5)
                    data, server_ip_port = client_sock.recvfrom(fragment_size)
                except socket.timeout:
                    print("Klient nedostal po 0.5 sekundy od servera ACK aleo ERR fragment")
                    client_sock.close()
                parsed_data = parse_data(data)
                result = check_crc(data)
                if result == 1:
                    if parsed_data['flag'] == ACK:
                        correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                    elif parsed_data['flag'] == ERR:
                        correctly_sent_fragments = correctly_sent_fragments + (already_sent_fragments - parsed_data[
                            'count_of_fragments'])  # correctly_sent_fragments = 6
                        switcher = 1
                    already_sent_fragments = 0
                    sequence_num += 1
                elif result == 0:
                    # VYTVARANIE ERR FRAGMENTU
                    header = create_header(ERR, sequence_num, 0, 0)
                    crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                    err_message = crc16.to_bytes(2, 'big') + header
                    # KONIEC VYTVARANIA ERR FRAGMENTU
                    sequence_num += 2
                    client_sock.sendto(err_message, (server_ip, server_port))
                    # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
                    try:
                        client_sock.settimeout(0.5)
                        data, server_ip_port = client_sock.recvfrom(fragment_size)
                    except socket.timeout:
                        print("Klient nedostal po 0.5 sekundy od servera ACK aleo ERR fragment")
                        client_sock.close()
                    parsed_data = parse_data(data)
                    result = check_crc(data)
                    if result == 1:
                        if parsed_data['flag'] == ACK:
                            correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                        elif parsed_data['flag'] == ERR:
                            correctly_sent_fragments = correctly_sent_fragments + (already_sent_fragments - parsed_data['count_of_fragments'])  # correctly_sent_fragments = 6
                            switcher = 1
                        already_sent_fragments = 0
                        sequence_num += 1
                    elif result == 0:
                        # VYTVARANIE ERR FRAGMENTU
                        header = create_header(ERR, sequence_num, 0, 0)
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        err_message = crc16.to_bytes(2, 'big') + header
                        # KONIEC VYTVARANIA ERR FRAGMENTU
                        client_sock.sendto(err_message, (server_ip, server_port))
                        print("ACK alebo ERR fragment od servera prisiel 2-krat nespravne, klient uzatvara komunikaciu")
                        client_sock.close()
                        errors = 2
            index += 1
        if errors == 0:
            sent_fragments.clear()
            # DRUHA KOMUNIKACIA
            # CLIENT POSIELA FRAGMENTY DAT SUBORU
            # VYTVARANIE INF FRAGMENTU
            header = create_header(INF, 0, count_of_file_fragments, data_size)
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
                sequence_num, parsed_data = inf_send2(parsed_data, client_sock, server_ip, server_port, fragment_size, count_of_file_fragments, data_size)

            # AK INF PRISIEL NA SERVER SPRAVNE, TAK CLIENT POSIELA FRAGMENTY
            if parsed_data['flag'] == ACK:
                sent_fragments = {}  # DICITONARY ODOSLANYCH FRAGMENTOV JEDNEHO BLOKU
                correctly_sent_fragments = 0
                already_sent_fragments = 0
                switcher = 0
                errors2 = 0
                # ZACIATOK DRUHEJ KOMUNIKACIE
                # CLIENT POSIELA FRAGMENTY S MENOM SUBORU
                with open(file_name, "rb") as file:
                    not_byte = 1
                    while correctly_sent_fragments != count_of_file_fragments and errors2 == 0:
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
                            try:
                                client_sock.settimeout(0.5)
                                data, server_ip_port = client_sock.recvfrom(fragment_size)
                            except socket.timeout:
                                print("Klient nedostal po 0.5 sekundy od servera ACK aleo ERR fragment")
                                client_sock.close()
                            parsed_data = parse_data(data)
                            result = check_crc(data)
                            if result == 1:
                                if parsed_data['flag'] == ACK:
                                    correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                                elif parsed_data['flag'] == ERR:
                                    correctly_sent_fragments = correctly_sent_fragments + (
                                                already_sent_fragments - parsed_data[
                                            'count_of_fragments'])  # correctly_sent_fragments = 6
                                    switcher = 1
                                already_sent_fragments = 0
                                sequence_num += 1
                            elif result == 0:
                                # VYTVARANIE ERR FRAGMENTU
                                header = create_header(ERR, sequence_num, 0, 0)
                                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                err_message = crc16.to_bytes(2, 'big') + header
                                # KONIEC VYTVARANIA ERR FRAGMENTU
                                sequence_num += 2
                                client_sock.sendto(err_message, (server_ip, server_port))
                                # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
                                try:
                                    client_sock.settimeout(0.5)
                                    data, server_ip_port = client_sock.recvfrom(fragment_size)
                                except socket.timeout:
                                    print("Klient nedostal po 0.5 sekundy od servera ACK aleo ERR fragment")
                                    client_sock.close()
                                parsed_data = parse_data(data)
                                result = check_crc(data)
                                if result == 1:
                                    if parsed_data['flag'] == ACK:
                                        correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                                    elif parsed_data['flag'] == ERR:
                                        correctly_sent_fragments = correctly_sent_fragments + (
                                                    already_sent_fragments - parsed_data[
                                                'count_of_fragments'])  # correctly_sent_fragments = 6
                                        switcher = 1
                                    already_sent_fragments = 0
                                    sequence_num += 1
                                elif result == 0:
                                    # VYTVARANIE ERR FRAGMENTU
                                    header = create_header(ERR, sequence_num, 0, 0)
                                    crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                    err_message = crc16.to_bytes(2, 'big') + header
                                    # KONIEC VYTVARANIA ERR FRAGMENTU
                                    client_sock.sendto(err_message, (server_ip, server_port))
                                    print(
                                        "ACK alebo ERR fragment od servera prisiel 2-krat nespravne, klient uzatvara komunikaciu")
                                    client_sock.close()
                                    errors2 = 2
            elif parsed_data['flag'] == ERR:
                client_sock.close()
                print("INF fragment sa po 3 pokusoch nepodarilo dorucit")
    elif parsed_data['flag'] == ERR:
        client_sock.close()
        print("INF fragment sa po 3 pokusoch nepodarilo dorucit")

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

def server(server_sock, fragment_size_for_server, path):
    type_of_input = 0
    count_of_fragments = 0

    # SERVER ZACINA POCUVAT NA "server_sock"
    #server_sock.bind((server_ip, server_port))

    # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
    data, client_ip_port = server_sock.recvfrom(fragment_size_for_server)

    # PARSOVANIE INF FRAGMENTU
    parsed_data = parse_data(data)

    # KONTROLA CI PRISIEL INF FRAGMENT SPRAVNE
    result = check_crc(data)

    # INF FRAGMENT PRISIEL NESPRAVNE
    if result == 0:
        result, parsed_data = inf_receive2(result, parsed_data, server_sock, client_ip_port, fragment_size_for_server)

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
            errors = 0
            count_of_accepted_fragments = 1
            last_data = create_header(ACK, parsed_data['sequence']+1, 0, 0)
            # SERVER PRIJIMA OD CLIENTA "count_of_fragments" DAT FRAGMENTOV
            while len(heap_file_name) != count_of_fragments and errors != 2:
                data, client_ip_port = server_sock.recvfrom(fragment_size_for_server)
                parsed_data = parse_data(data)

                # SERVER PRIJAL DAT FRAGMENT
                if parsed_data['flag'] == DAT:
                    result = check_crc(data)
                    # SERVER PRIJAL CHYBNY FRAGMENT
                    if result == 0:
                        # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV  # test1.txt
                        error_results.append(parsed_data['sequence'])  # 12                       # 12 13 14 15 16 17 18
                        error_results_heap.append(parsed_data['sequence'])  # 12 15
                    # SERVER PRIJAL NEPOSKODENY FRAGMENT
                    elif result == 1:
                        # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                        # heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data'].decode('utf-8')))
                        heapq.heappush(heap_file_name, (parsed_data['sequence'], parsed_data['data']))  # (e, 13) (s, 14) (1, 16)
                        print("spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                        count_of_accepted_fragments += 1

                # SERVER PRIJAL SAG FRAGMENT
                elif parsed_data['flag'] == SAG:
                    result = check_crc(data)
                    # SERVER PRIJAL CHYBNY FRAGMENT
                    if result == 0:
                        error_results.append(parsed_data['sequence'])  # 12
                    elif result == 1:
                        # heapq.heappush(heap_file_name, (error_results_heap[sag_flags], parsed_data['data'].decode('utf-8')))
                        heapq.heappush(heap_file_name, (error_results_heap[sag_flags], parsed_data['data']))
                        print("original sequence - ", error_results_heap[sag_flags], "spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "sequence: ", parsed_data['sequence'], "    ", "data", parsed_data['data'])
                        count_of_accepted_fragments += 1
                        print(error_results_heap)
                        error_results_heap.pop(sag_flags)
                        sag_flags -= 1
                    sag_flags += 1


                # SERVER PRIJAL ERR FRAGMENT
                elif parsed_data['flag'] == ERR:
                    server_sock.sendto(last_data, client_ip_port)
                    index = 0  # 0
                    errors += 1  # 2
                    if errors == 2:
                        print("ERR fragment od klienta prisiel 2-krat nespravne, server uzatvara komunikaciu")
                        server_sock.close()


                # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                if index == 5 or (len(error_results) + len(heap_file_name) == count_of_fragments):
                    sag_flags = 0
                    index = 0
                    errors = 0
                    # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA CLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
                    if len(error_results) > 0:
                        # VYTVARANIE ERR FRAGMENTU
                        header = create_header(ERR, parsed_data['sequence']+1, len(error_results), len(error_results)*3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                        data_of_fragment = bytes()
                        for fragment in error_results:
                            data_of_fragment += fragment.to_bytes(3, 'big')
                        last_data = data_of_fragment
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
                        last_data = header
                        crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                        ack_message = crc16.to_bytes(2, 'big') + header
                        # KONIEC VYTVARANIA ACK FRAGMENTU
                        # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                        server_sock.sendto(ack_message, client_ip_port)
                index += 1  # 1

            if errors != 2:
                # SKLADANIE MENA SUBORU Z BINARNEJ HALDY
                file_name = ""
                while heap_file_name:
                    file_name += heapq.heappop(heap_file_name)[1].decode('utf-8')
                print(file_name)

                # DRUHA KOMUNIKACIA
                # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
                data, client_ip_port = server_sock.recvfrom(fragment_size_for_server)

                # PARSOVANIE INF FRAGMENTU
                parsed_data = parse_data(data)

                # KONTROLA CI PRISIEL INF FRAGMENT SPRAVNE
                result = check_crc(data)

                # INF FRAGMENT PRISIEL NESPRAVNE
                if result == 0:
                    result, parsed_data = inf_receive2(result, parsed_data, server_sock, client_ip_port, fragment_size_for_server)

                # INF FRAGMENT PRISIEL SPRAVNE
                if result == 1:
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
                        errors2 = 0
                        while len(heap_file_name) != count_of_file_fragments and errors2 != 2:
                            # SERVER PRIJIMA OD CLIENTA "count_of_file_fragments" DAT FRAGMENTOV
                            data, client_ip_port = server_sock.recvfrom(fragment_size_for_server)
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

                            # SERVER PRIJAL ERR FRAGMENT
                            elif parsed_data['flag'] == ERR:
                                server_sock.sendto(last_data, client_ip_port)
                                index = 0  # 0
                                errors2 += 1  # 2
                            if errors2 == 2:
                                print("ERR fragment od klienta prisiel 2-krat nespravne, server uzatvara komunikaciu")
                                server_sock.close()

                            # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                            if index == 5 or (len(error_results) + len(heap_file_name) == count_of_file_fragments):
                                sag_flags = 0
                                index = 0
                                errors2 = 0
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
                        if errors2 != 2:
                            print("ZACINAM VKLADAT DATA DO SUBORU")
                            with open(os.path.join(path, file_name), 'wb') as fp:
                                while heap_file_name:
                                    fp.write(heapq.heappop(heap_file_name)[1])
                            print("Dokoncene")

                elif result == 0:
                    server_sock.close()
                    print("Informacny fragment po 3 pokusoch neprisiel spravne")
        elif type_of_input == 1:  # SPRAVA
            pass
    elif result == 0:
        server_sock.close()
        print("Informacny fragment po 3 pokusoch neprisiel spravne")

def keep_alive_sends_kpa(server_ip, server_port, client_sock):
    header = create_header(KPA, 0, 0, 0)
    crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
    kpa_message = crc16.to_bytes(2, 'big') + header
    try:
        #print("[KLIENT] posielam - KEEP ALIVE")
        client_sock.sendto(kpa_message, (server_ip, server_port))
        client_sock.settimeout(2)
        data, server_ip_port = client_sock.recvfrom(SIZE_OF_HEADER+SIZE_OF_CRC)
        parsed_data = parse_data(data)
        if parsed_data['flag'] == ACK:
            #print("[KLIENT] prijimam - ACK na KEEP ALIVE")
            return 1
    except socket.timeout:
        return 0


def keep_alive_client(server_ip, server_port, client_sock):
    result = keep_alive_sends_kpa(server_ip, server_port, client_sock)
    while result == 1:  # Prijimam ACK
        time.sleep(10)
        result = keep_alive_sends_kpa(server_ip, server_port, client_sock)
        """thread = threading.Timer(10, keep_alive_client, args=(server_ip, server_port, client_sock))
        thread.start()"""
    if result == 0:
        print("[KLIENT] Server pocas KEEP ALIVE neopovedal")
        client_sock.close()

def keep_alive_server(server_sock, fragment_size_server):
    data, client_ip_port = server_sock.recvfrom(fragment_size_server)
    #print("[SERVER] prijimam - KEEP ALIVE")
    parsed_data = parse_data(data)
    while parsed_data['flag'] == KPA:
        try:
            # VYTVARANIE ACK FRAGMENTU NA ODPOVEDANIE CLIENTOVI, ZE INF FRAGMENT PRISIEL SPAVNE
            header = create_header(ACK, 0, 0, 0)
            crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
            ack_message = crc16.to_bytes(2, 'big') + header
            # KONIEC VYTVARANIA ACK FRAGMENTU

            # ODOSLANIE ACK FRAGMENTU CLIENTOVI
            #print("[SERVER] posielam - ACK na KEEP ALIVE")
            server_sock.sendto(ack_message, client_ip_port)  # SERVER posiela ACK
            server_sock.settimeout(12)
            data, client_ip_port = server_sock.recvfrom(fragment_size_server)
            #print("[SERVER] prijimam - KEEP ALIVE")
            parsed_data = parse_data(data)
        except socket.timeout:
            print("[SERVER] KEEP ALIVE od klienta neprisiel, uzatvaram komunikaciu")
            server_sock.close()


client_sock = socket.socket()
server_sock = socket.socket()
thread = threading.Timer(None, None)
thread2 = threading.Timer(None, None)
life = 1
count_of_servers = 0
count_of_clients = 0
while life > 0:
    print("1 -> Klient")
    print("2 -> Server")
    option = int(input("Zadajte svoju ulohu: "))  # 1 alebo 2
    data_size = 100  # int(input("Zadajte velkost dat v Bytoch: "))
    server_ip = "localhost"  # input("Zadajte cielovu IP adresu: ")
    server_port = 5005  # int(input("Zadajte cielovy port: "))

    # *KLIENT*
    if option == 1:
        # max velkost fragmentu je 1500 - 28 (IP + UDP header) - 9 (moja hlavicka) - 2 (CRC) = 1461
        fragment_size_client = data_size + SIZE_OF_HEADER + SIZE_OF_CRC + 15  # CLIENT moze prijat ERR packet, v ktorom bude 5 chybnych fragmentov so svojim sequence (kazdy ma 3 Byty)
        #print("1 -> Sprava")
        #print("2 -> Subor")
        type_of_input = 2  #int(input("Zadajte svoj vyber: "))

        if life > 1:
            thread.cancel()
            thread2.cancel()
            server_sock.close()
            client_sock.close()
        if count_of_clients == 0:
            client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        if type_of_input == 1:  # SPRAVA
            message = "Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS ! Hello PKS !"  # input
            client_sends_msg(data_size, fragment_size_client, server_ip, server_port, type_of_input, client_sock, message)
        elif type_of_input == 2:  # SUBOR
            file_name = "test1.txt"  # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
            client_sends_file(data_size, fragment_size_client, server_ip, server_port, type_of_input, client_sock, file_name)
            #keep_alive_client(server_ip, server_port, client_sock)
            thread = threading.Timer(10, keep_alive_client, args=(server_ip, server_port, client_sock))
            thread.start()
            print(thread)
            print("[KLIENT] spustam na pozadi KEEP ALIVE")
        # subor doposielany


    # *SERVER*
    elif option == 2:
        fragment_size_server = data_size + SIZE_OF_HEADER + SIZE_OF_CRC
        path = 'C:/Users/adamf/Desktop/PKS_files'

        if life > 1:
            pass
            #server_sock.close()
            #thread.cancel()
            #thread2.cancel()
            #client_sock.close()


        if count_of_servers == 0:
            server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            server_sock.bind((server_ip, server_port))
            count_of_servers = 1

        server(server_sock, fragment_size_server, path)
        # subor doposielany
        thread2 = threading.Timer(0, keep_alive_server, args=(server_sock, fragment_size_server))
        thread2.start()
        print(thread2)
        print("[SERVER] spustam na pozadi KEEP ALIVE")

    life += 1
