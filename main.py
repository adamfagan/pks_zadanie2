import socket
import os
import heapq
import threading
from random import randint
from crc16 import GetCrc16
thread = threading.Thread

terminate_event = threading.Event()

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
    # testovanie s 50% sancou chybneho CRC
    """if randint(0, 100) > 50:
        new_crc = GetCrc16(str(123456789))  # Na testovanie CRC
    else:
        new_crc = GetCrc16(str(int.from_bytes(data[2:], 'big')))"""
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

    flg = flag.to_bytes(1, 'big')
    sqn = sequence_num.to_bytes(3, 'big')
    cof = count_fragments.to_bytes(3, 'big')
    fgs = data_size.to_bytes(2, 'big')
    return flg + sqn + cof + fgs

def calculate_fragments(type_of_input, data_size, file_or_msg):
    # SPRAVA
    if type_of_input == 1:
        count_of_fragments = len(file_or_msg) / data_size
        if count_of_fragments > int(count_of_fragments):
            return int(count_of_fragments) + 1
        else:
            return int(count_of_fragments)
    # SUBOR
    elif type_of_input == 2:
        size_of_file = os.path.getsize(file_or_msg)
        if size_of_file / data_size > int(size_of_file / data_size):
            return int(size_of_file / data_size) + 1
        else:
            return int(size_of_file / data_size)

def client_sends_msg(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, message):
    count_of_fragments_msg = calculate_fragments(type_of_input, data_size, message)  # zistenie poctu posielanych fragmentov
    sequence_num_msg = 0

    # ZACIATOK KOMUNIKACIE

    # CLIENT POSIELA FRAGMENTY S NAZVOM SUBORU
    # VYTVARANIE INF FRAGMENTU
    header = create_header(INF, sequence_num_msg, count_of_fragments_msg, data_size)
    header_and_data = header + (1).to_bytes(1, 'big')
    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
    inf_message = crc16.to_bytes(2, 'big') + header_and_data
    # KONIEC VYTVARANIA INF FRAGMENTU

    # ODOSLANIE INF FRAGMENTU SERVERU
    client_sock.sendto(inf_message, (server_ip, server_port))

    # CLIENT OCAKAVA ACK FRAGMENT OD SERVERA
    data, server_ip_port = client_sock.recvfrom(fragment_size)
    parsed_data = parse_data(data)
    sequence_num_msg += 2

    # AK INF PRISIEL NA SERVER SPRAVNE, TAK CLIENT POSIELA FRAGMENTY
    if parsed_data['flag'] == ACK:
        sent_fragments_msg = {}  # dictionary odoslanych fragmentov
        index = 0
        correctly_sent_fragments = 0
        already_sent_fragments = 0
        switcher = 0

        # ZACIATOK PRVEJ KOMUNIKACIE
        # KLIENT POSIELA FRAGMENTY SPRAVY
        while correctly_sent_fragments != count_of_fragments_msg:
            if switcher == 1:
                i = 0
                while i < parsed_data['data_size']:
                    sequence = int.from_bytes(parsed_data['data'][i:i + 3], 'big')
                    # VYTVARANIE SAG FRAGMENTU
                    header = create_header(SAG, sequence, count_of_fragments_msg, data_size)
                    # VYBRANIE SAG URCITEHO ZLE ODOSLANEHO FRAGMENTU
                    data_of_fragment = sent_fragments_msg.get(sequence)
                    header_and_data = header + data_of_fragment
                    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                    dat_message = crc16.to_bytes(2, 'big') + header_and_data
                    # KONIEC VYTVARANIA SAG FRAGMENTU
                    # ODOSLANIE DAT FRAGMENTU SERVERU
                    client_sock.sendto(dat_message, (server_ip, server_port))
                    print("[KLIENT] Posielam fragment znova", "      ", "Poradie fragmentu: ",  sequence_num_msg, "      ", "Povodne poradie fragmentu: ", sequence, "      ", "Velkost: ", data_size, "[Byte]", "      ", "Data: ", data_of_fragment)
                    already_sent_fragments += 1
                    sent_fragments_msg[sequence_num_msg] = data_of_fragment
                    sequence_num_msg += 1
                    i += 3
                switcher = 0

            if index < count_of_fragments_msg:  # index oznacuje pocet poslanych fragmentov
                # VYTVARANIE DAT FRAGMENTU
                header = create_header(DAT, sequence_num_msg, count_of_fragments_msg, data_size)
                data_of_fragment = bytes(message[index*data_size:data_size+(index*data_size)], 'utf-8')
                header_and_data = header + data_of_fragment
                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                dat_message = crc16.to_bytes(2, 'big') + header_and_data
                # KONIEC VYTVARANIA DAT FRAGMENTU
                # ODOSLANIE DAT FRAGMENTU SERVERU
                client_sock.sendto(dat_message, (server_ip, server_port))
                print("[KLIENT] Posielam novy fragment", "      ", "Poradie fragmentu: ", sequence_num_msg, "      ",
                        "Velkost: ", data_size, "[Byte]", "      ", "Data: ", data_of_fragment)
                already_sent_fragments += 1
                sent_fragments_msg[sequence_num_msg] = data_of_fragment
                # ULOZENIE SI PRAVE ODOSLANEHO DAT FRAGMENTU
                sequence_num_msg += 1

            # PRIJIMANIE ACK ALEBO ERR FRAGMENTU PO ODOSLANI KAZDYCH 5 FRAGMENTOV
            if already_sent_fragments == 5 or (index >= count_of_fragments_msg):
                # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
                data, server_ip_port = client_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)
                if parsed_data['flag'] == ACK:
                    correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                elif parsed_data['flag'] == ERR:
                    correctly_sent_fragments = correctly_sent_fragments + (
                                already_sent_fragments - parsed_data['count_of_fragments'])
                    switcher = 1
                already_sent_fragments = 0
                sequence_num_msg += 1
            index += 1
        sent_fragments_msg.clear()


def client_sends_file(data_size, fragment_size, server_ip, server_port, type_of_input, client_sock, file_name):
    count_of_name_fragments = calculate_fragments(1, data_size, file_name)  # type = 1 -> fragmentuje ako string
    count_of_file_fragments = calculate_fragments(type_of_input, data_size, file_name)
    sequence_num = 0

    # ZACIATOK KOMUNIKACIE

    # KLIENT POSIELA INF FRAGMENT O NAZVE SUBORU
    # VYTVARANIE INF FRAGMENTU
    header = create_header(INF, sequence_num, count_of_name_fragments, data_size)
    header_and_data = header + (2).to_bytes(1, 'big')
    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
    inf_message = crc16.to_bytes(2, 'big') + header_and_data
    # KONIEC VYTVARANIA INF FRAGMENTU

    # ODOSLANIE INF FRAGMENTU SERVERU
    client_sock.sendto(inf_message, (server_ip, server_port))

    # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
    data, server_ip_port = client_sock.recvfrom(fragment_size)
    parsed_data = parse_data(data)
    sequence_num += 2

    # AK INF PRISIEL NA SERVER SPRAVNE, TAK CLIENT POSIELA FRAGMENTY
    if parsed_data['flag'] == ACK:
        sent_fragments = {}  # DICITONARY ODOSLANYCH FRAGMENTOV
        index = 0
        correctly_sent_fragments = 0
        already_sent_fragments = 0
        switcher = 0

        # ZACIATOK PRVEJ KOMUNIKACIE
        # KLIENT POSIELA FRAGMENTY S NAZVOM SUBORU
        while correctly_sent_fragments != count_of_name_fragments:
            if switcher == 1:
                i = 0
                while i < parsed_data['data_size']:
                    sequence = int.from_bytes(parsed_data['data'][i:i+3], 'big')
                    # VYTVARANIE SAG FRAGMENTU
                    header = create_header(SAG, sequence, count_of_name_fragments, data_size)
                    # VYBRANIE SAG URCITEHO ZLE ODOSLANEHO FRAGMENTU
                    data_of_fragment = sent_fragments.get(sequence)
                    header_and_data = header + data_of_fragment
                    crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                    dat_message = crc16.to_bytes(2, 'big') + header_and_data
                    # KONIEC VYTVARANIA SAG FRAGMENTU
                    # ODOSLANIE DAT FRAGMENTU SERVERU
                    client_sock.sendto(dat_message, (server_ip, server_port))
                    print("[KLIENT] Posielam fragment znova", "      ", "Poradie fragmentu: ", sequence_num,
                          "      ", "Povodne poradie fragmentu: ", sequence, "      ", "Velkost: ", data_size, "[Byte]",
                          "      ", "Data: ", data_of_fragment)
                    # testovanie posielania kazdeho neparneho
                    """if sequence_num % 2 == 0:
                        print("neposlany INDEX -  ", sequence, "data", data_of_fragment)
                        #sequence_num -= 1
                        time.sleep(2)
                        #client_sock.sendto(dat_message, (server_ip, server_port))
                    else:
                        print("SEQ 3 = ", sequence_num)
                        print("Odoslal som znova - ", sequence, "data", sent_fragments.get(sequence))
                        client_sock.sendto(dat_message, (server_ip, server_port))"""
                    already_sent_fragments += 1
                    sent_fragments[sequence_num] = data_of_fragment
                    sequence_num += 1
                    i += 3
                switcher = 0

            if index < count_of_name_fragments:  # index oznacuje pocet poslanych fragmentov
                # VYTVARANIE DAT FRAGMENTU
                header = create_header(DAT, sequence_num, count_of_name_fragments, data_size)
                data_of_fragment = bytes(file_name[index*data_size:data_size+(index*data_size)], 'utf-8')
                header_and_data = header + data_of_fragment
                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                dat_message = crc16.to_bytes(2, 'big') + header_and_data
                # KONIEC VYTVARANIA DAT FRAGMENTU
                # ODOSLANIE DAT FRAGMENTU SERVERU
                # Odkomentujte pre testovanie posielania kazdeho neparneho
                """if sequence_num % 2 == 0:
                    #print(index)
                    print("neposlany INDEX - ", sequence_num, "data", data_of_fragment)
                    #sequence_num -= 1
                    time.sleep(3)
                    #client_sock.sendto(dat_message, (server_ip, server_port))
                else:
                    print("Odoslal som prvykrat - ", sequence_num, "data", file_name[index:index+data_size])
                    client_sock.sendto(dat_message, (server_ip, server_port))"""
                client_sock.sendto(dat_message, (server_ip, server_port))
                print("[KLIENT] Posielam novy fragment", "      ", "Poradie fragmentu: ", sequence_num, "      ",
                      "Velkost: ", data_size, "[Byte]", "      ", "Data: ", data_of_fragment)
                already_sent_fragments += 1
                # ULOZENIE SI PRAVE ODOSLANEHO DAT FRAGMENTU
                sent_fragments[sequence_num] = data_of_fragment
                sequence_num += 1

            # PRIJIMANIE ACK ALEBO ERR FRAGMENTU PO ODOSLANI KAZDYCH 5 FRAGMENTOV
            if already_sent_fragments == 5 or (index >= count_of_name_fragments):
                data, server_ip_port = client_sock.recvfrom(fragment_size)
                parsed_data = parse_data(data)
                if parsed_data['flag'] == ACK:
                    correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                elif parsed_data['flag'] == ERR:
                    correctly_sent_fragments = correctly_sent_fragments + (already_sent_fragments - parsed_data['count_of_fragments'])
                    switcher = 1
                already_sent_fragments = 0
                sequence_num += 1
            index += 1

        sent_fragments.clear()

        # DRUHA KOMUNIKACIA
        # CLIENT POSIELA FRAGMENTY SUBORU
        # VYTVARANIE INF FRAGMENTU
        header = create_header(INF, 0, count_of_file_fragments, data_size)
        header_and_data = header + (2).to_bytes(1, 'big')
        crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
        inf_message = crc16.to_bytes(2, 'big') + header_and_data
        # KONIEC VYTVARANIA INF FRAGMENTU

        # ODOSLANIE INF FRAGMENTU SERVERU
        client_sock.sendto(inf_message, (server_ip, server_port))

        # CLIENT OCAKAVA ACK ALEBO ERR FRAGMENT OD SERVERA
        data, server_ip_port = client_sock.recvfrom(fragment_size)
        parsed_data = parse_data(data)

        if parsed_data['flag'] == ACK:
            correctly_sent_fragments = 0
            already_sent_fragments = 0
            switcher = 0
            # ZACIATOK DRUHEJ KOMUNIKACIE
            # CLIENT POSIELA FRAGMENTY S NAZVOM SUBORU
            with open(file_name, "rb") as file:
                not_byte = 1
                while correctly_sent_fragments != count_of_file_fragments:
                    if switcher == 1:
                        i = 0
                        while i < parsed_data['data_size']:
                            sequence = int.from_bytes(parsed_data['data'][i:i + 3], 'big')
                            # VYTVARANIE SAG FRAGMENTU
                            header = create_header(SAG, sequence, count_of_file_fragments, data_size)
                            # VYBRANIE SAG URCITEHO ZLE ODOSLANEHO FRAGMENTU
                            data_of_fragment = sent_fragments.get(sequence)
                            header_and_data = header + data_of_fragment
                            crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                            dat_message = crc16.to_bytes(2, 'big') + header_and_data
                            # KONIEC VYTVARANIA SAG FRAGMENTU
                            # ODOSLANIE SAG FRAGMENTU SERVERU
                            client_sock.sendto(dat_message, (server_ip, server_port))
                            print("[KLIENT] Posielam fragment znova", "      ", "Poradie fragmentu: ", sequence_num,
                                  "      ", "Povodne poradie fragmentu: ", sequence, "      ", "Velkost: ", data_size,
                                  "[Byte]", "      ", "Data: ", data_of_fragment)
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
                        print("[KLIENT] Posielam novy fragment", "      ", "Poradie fragmentu: ", sequence_num,
                              "      ",
                              "Velkost: ", data_size, "[Byte]", "      ", "Data: ", data_of_fragment)
                        already_sent_fragments += 1
                        sent_fragments[sequence_num] = data_of_fragment
                        sequence_num += 1

                    if (already_sent_fragments == 5) or (not_byte == 0):
                        data, server_ip_port = client_sock.recvfrom(fragment_size)
                        parsed_data = parse_data(data)
                        if parsed_data['flag'] == ACK:
                            correctly_sent_fragments = correctly_sent_fragments + already_sent_fragments
                        elif parsed_data['flag'] == ERR:
                            correctly_sent_fragments = correctly_sent_fragments + (
                                        already_sent_fragments - parsed_data['count_of_fragments'])
                            switcher = 1
                        already_sent_fragments = 0
                        sequence_num += 1


def server(server_sock, path, ip_port):
    new_inf = 0

    choose_s = input(f"[y/n] Chcete pocuvat na porte ? {ip_port[1]} : ")

    if choose_s == 'n':
        return 1

    while True:
        type_of_input = 0
        count_of_fragments = 0
        server_sock.settimeout(None)

        while True:
            # SERVER OCAKAVA INF FRAGMENT OD CLIENTA
            if new_inf == 0:
                print("NEW_inf", new_inf)
                data, client_ip_port = server_sock.recvfrom(2048)

            # PARSOVANIE INF FRAGMENTU
            parsed_data = parse_data(data)

            new_inf = 0
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

            # SERVER PRIJIMA SUBOR
            if type_of_input == 2:
                file_name = ""
                received_msg = []     # binarna halda na ukladanie mena suboru
                heapq.heapify(received_msg)
                error_results = []      # pole na ukladanie chybnych fragmentov
                error_results_heap = []
                sag_flags = 0
                error_results_size = 0
                index = 0
                count_of_accepted_fragments = 1
                sequence_num = parsed_data['sequence']+2

                # SERVER PRIJIMA OD KLIENTA FRAGMENTY MENA SUBORU
                while len(received_msg) != count_of_fragments:
                    server_sock.settimeout(10)
                    try:
                        data, client_ip_port = server_sock.recvfrom(2048)
                        parsed_data = parse_data(data)

                        # SERVER PRIJAL DAT FRAGMENT
                        if parsed_data['flag'] == DAT:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY DAT FRAGMENT
                            if result == 0:
                                # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV
                                error_results.append(parsed_data['sequence'])
                                error_results_heap.append(parsed_data['sequence'])
                            # SERVER PRIJAL NEPOSKODENY DAT FRAGMENT
                            elif result == 1:
                                # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                                heapq.heappush(received_msg, (parsed_data['sequence'], parsed_data['data']))
                                print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "Poradie fragmentu: ", parsed_data['sequence'], "    ", "Velkost: ", parsed_data['data_size'], "[Byte]", "data", parsed_data['data'])
                                count_of_accepted_fragments += 1

                        # SERVER PRIJAL SAG FRAGMENT
                        elif parsed_data['flag'] == SAG:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY SAG FRAGMENT
                            if result == 0:
                                error_results.append(parsed_data['sequence'])
                            # SERVER PRIJAL NEPOSKODENY SAG FRAGMENT
                            elif result == 1:
                                # testovanie kazdeho neparneho
                                """heapq.heappush(received_msg, (error_results[index], parsed_data['data']))  # (e, 13) (s, 14) (1, 16)
                                print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "Poradie fragmentu: ", parsed_data['sequence'], "    ", "Velkost: ", parsed_data['data_size'], "[Byte]")
                                error_results.pop(index)"""

                                heapq.heappush(received_msg, (error_results_heap[sag_flags], parsed_data['data']))
                                print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ",
                                      "Poradie fragmentu: ", parsed_data['sequence'], "    ", "Velkost: ",
                                      parsed_data['data_size'], "[Byte]")
                                count_of_accepted_fragments += 1
                                error_results_heap.pop(sag_flags)
                                sag_flags -= 1
                            sag_flags += 1

                        # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT KLIENTOVI
                        if index == 4 or (len(error_results) + len(received_msg) == count_of_fragments):
                            index = -1
                            sag_flags = 0
                            # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA KLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
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
                                #error_results_size = len(error_results) - pre testovanie kazdeho neparneho
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

                    except socket.timeout:
                        print("[SERVER] Fragment od klienta neprisiel do 2 sekund")

                        if index < error_results_size:
                            pass
                        else:
                            error_results.append(sequence_num)

                        if index == 4 or (len(error_results) + len(received_msg) == count_of_fragments):
                            index = -1
                            sag_flags = 0
                            # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA CLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
                            if len(error_results) > 0:
                                # VYTVARANIE ERR FRAGMENTU
                                sequence_num += 1
                                header = create_header(ERR, sequence_num, len(error_results), len(error_results) * 3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                                data_of_fragment = bytes()
                                for fragment in error_results:
                                    data_of_fragment += fragment.to_bytes(3, 'big')
                                header_and_data = header + data_of_fragment
                                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                                err_message = crc16.to_bytes(2, 'big') + header_and_data
                                # KONIEC VYTVARANIA ERR FRAGMENTU
                                # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                                server_sock.sendto(err_message, client_ip_port)
                                error_results_size = len(error_results)
                            # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                            elif len(error_results) == 0:
                                # VYTVARANIE ACK FRAGMENTU
                                sequence_num += 1
                                header = create_header(ACK, sequence_num, 0, 0)
                                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                ack_message = crc16.to_bytes(2, 'big') + header
                                # KONIEC VYTVARANIA ACK FRAGMENTU
                                # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                                server_sock.sendto(ack_message, client_ip_port)
                        index += 1
                    sequence_num += 1

                # SKLADANIE MENA SUBORU Z BINARNEJ HALDY
                while received_msg:
                    file_name += heapq.heappop(received_msg)[1].decode('utf-8')
                # KONIEC SKLADANIA MENA

                # DRUHA KOMUNIKACIA
                # SERVER OCAKAVA INF FRAGMENT OD KLIENTA
                data, client_ip_port = server_sock.recvfrom(2048)

                # PARSOVANIE INF FRAGMENTU
                parsed_data = parse_data(data)

                if parsed_data['flag'] == INF:
                    count_of_file_fragments = parsed_data['count_of_fragments']

                    # VYTVARANIE ACK FRAGMENTU NA ODPOVEDANIE CLIENTOVI, ZE INF FRAGMENT PRISIEL SPAVNE
                    header = create_header(ACK, parsed_data['sequence']+1, 0, 0)
                    crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                    ack_message = crc16.to_bytes(2, 'big') + header
                    # KONIEC VYTVARANIA ACK FRAGMENTU

                    # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                    server_sock.sendto(ack_message, client_ip_port)  # SERVER posiela ACK

                    received_msg.clear()
                    heapq.heapify(received_msg)
                    error_results.clear()  # POLE NA UKLADANIE CHYBNYCH FRAGMENTOV
                    index = 1
                    total_size = 0
                    file_size = os.path.getsize(path)
                    error_results_heap.clear()
                    sag_flags = 0

                    while len(received_msg) != count_of_file_fragments:
                        # SERVER PRIJIMA OD CLIENTA "count_of_file_fragments" DAT FRAGMENTOV
                        server_sock.settimeout(10)
                        try:
                            data, client_ip_port = server_sock.recvfrom(2048)
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
                                    heapq.heappush(received_msg, (parsed_data['sequence'], parsed_data['data']))
                                    total_size += parsed_data['data_size']
                                    print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ", "Poradie fragmentu: ",
                                          parsed_data['sequence'], "    ", "Velkost: ", parsed_data['data_size'], "[Byte]", "    ", "Prijate: ", total_size, "[Byte]")
                                    count_of_accepted_fragments += 1

                            # SERVER PRIJAL SAG FRAGMENT
                            elif parsed_data['flag'] == SAG:
                                result = check_crc(data)
                                # SERVER PRIJAL CHYBNY SAG FRAGMENT
                                if result == 0:
                                    error_results.append(parsed_data['sequence'])
                                # SERVER PRIJAL NEPOSKODENY SAG FRAGMENT
                                elif result == 1:
                                    # testovanie kazdeho neparneho
                                    """heapq.heappush(received_msg, (error_results[index], parsed_data['data']))
                                    error_results.pop(index)
                                    error_results.pop(index)"""
                                    heapq.heappush(received_msg, (error_results_heap[sag_flags], parsed_data['data']))
                                    print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments,
                                          "    ", "Poradie fragmentu: ", parsed_data['sequence'], "    ",
                                          "Velkost: ", parsed_data['data_size'], "[Byte]")
                                    count_of_accepted_fragments += 1
                                    error_results_heap.pop(sag_flags)
                                    sag_flags -= 1
                                sag_flags += 1

                            # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT CLIENTOVI
                            if index == 5 or (len(error_results) + len(received_msg) == count_of_file_fragments):
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
                            index += 1
                        except socket.timeout:
                            print("[SERVER] Fragment od klienta neprisiel do 2 sekund")

                            if index < error_results_size:
                                pass
                            else:
                                error_results.append(sequence_num)

                            if index == 5 or (len(error_results) + len(received_msg) == count_of_file_fragments):
                                index = 0
                                sag_flags = 0
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
                            index += 1

                    # SKLADANIE MENA SUBORU Z BINARNEJ HALDY
                    print("")
                    print("[SERVER] Vkladam data do suboru")
                    with open(os.path.join(path, file_name), 'wb') as fp:
                        while received_msg:
                            fp.write(heapq.heappop(received_msg)[1])
                    print("[SERVER] Data boli uspesne vlozene do suboru")
                    print("[SERVER] Subor bol uspesne preneseny")
                    print("[SERVER] Cesta k suboru: ", path)
                    print("[SERVER] Nazov suboru: ", file_name)
                    break

            # SERVER PRIJIMA SPRAVU
            elif type_of_input == 1:
                received_msg = []  # binarna halda na ukladanie spravy
                heapq.heapify(received_msg)
                error_results = []  # pole na ukladanie chybnych fragmentov
                error_results_heap = []
                sag_flags = 0
                error_results_size = 0
                index = 0
                count_of_accepted_fragments = 1
                sequence_num = parsed_data['sequence'] + 2

                # SERVER PRIJIMA OD KLIENTA FRAGMENTY SPRAVY
                while len(received_msg) != count_of_fragments:
                    server_sock.settimeout(2)
                    try:
                        data, client_ip_port = server_sock.recvfrom(2048)
                        parsed_data = parse_data(data)

                        # SERVER PRIJAL DAT FRAGMENT
                        if parsed_data['flag'] == DAT:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY DAT FRAGMENT
                            if result == 0:
                                # PRIDANIE SEQUENCE (PORADIE) CHYBNEHO FRAGMENTU DO POLA CHYBNYCH FRAGMETOV
                                error_results.append(parsed_data['sequence'])
                                error_results_heap.append(parsed_data['sequence'])
                            # SERVER PRIJAL NEPOSKODENY DAT FRAGMENT
                            elif result == 1:
                                # PRIDANIE SEQUENCE (PORADIE) A DAT NEPOSKODENEHO FRAGMETU DO BINARNEJ HALDY
                                heapq.heappush(received_msg, (parsed_data['sequence'], parsed_data['data']))
                                print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ",
                                      "Poradie fragmentu: ", parsed_data['sequence'], "    ", "Velkost: ",
                                      parsed_data['data_size'], "[Byte]", "data", parsed_data['data'])
                                count_of_accepted_fragments += 1

                        # SERVER PRIJAL SAG FRAGMENT
                        elif parsed_data['flag'] == SAG:
                            result = check_crc(data)
                            # SERVER PRIJAL CHYBNY SAG FRAGMENT
                            if result == 0:
                                error_results.append(parsed_data['sequence'])
                            # SERVER PRIJAL NEPOSKODENY SAG FRAGMENT
                            elif result == 1:
                                # testovanie kazdeho nepareho
                                # heapq.heappush(received_msg, (error_results_heap[sag_flags], parsed_data['data']))
                                # error_results.pop(index)
                                heapq.heappush(received_msg, (error_results_heap[sag_flags], parsed_data['data']))
                                print("[SERVER] Spravne prijaty fragment: ", count_of_accepted_fragments, "    ",
                                      "Poradie fragmentu: ", parsed_data['sequence'], "    ", "Velkost: ",
                                      parsed_data['data_size'], "[Byte]")
                                count_of_accepted_fragments += 1
                                error_results_heap.pop(sag_flags)
                                sag_flags -= 1
                            sag_flags += 1

                        # PO KAZDYCH 5 PRIJATYCH FRAGMENTOCH ODOSIELA SERVER ACK ALEBO ERR FRAGMENT KLIENTOVI
                        if index == 4 or (len(error_results) + len(received_msg) == count_of_fragments):
                            index = -1
                            sag_flags = 0
                            # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA KLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
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
                                print(error_results)
                                error_results_size = len(error_results)
                                error_results.clear()
                            # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                            elif len(error_results) == 0:
                                # VYTVARANIE ACK FRAGMENTU
                                header = create_header(ACK, parsed_data['sequence'] + 1, 0, 0)
                                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                ack_message = crc16.to_bytes(2, 'big') + header
                                # KONIEC VYTVARANIA ACK FRAGMENTU
                                # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                                server_sock.sendto(ack_message, client_ip_port)
                        index += 1

                    except socket.timeout:
                        print("[SERVER] Fragment od klienta neprisiel do 2 sekund")
                        if index < error_results_size:
                            pass
                        else:
                            error_results.append(sequence_num)

                        if index == 4 or (len(error_results) + len(received_msg) == count_of_fragments):
                            index = -1
                            # AK BOLI PRIJATE NEJAKE CHYBNE DAT FRAGMENTY, TAK SERVER POSIELA CLIENTOVI ERR FRAGMENT S CHYBNE PRIJATYMI FRAGMENTMI
                            if len(error_results) > 0:
                                # VYTVARANIE ERR FRAGMENTU
                                sequence_num += 1
                                header = create_header(ERR, sequence_num, len(error_results), len(
                                    error_results) * 3)  # *3 PRETOZE KAZDY SEQUENCE ZABERA 3 BYTY
                                data_of_fragment = bytes()
                                for fragment in error_results:
                                    data_of_fragment += fragment.to_bytes(3, 'big')
                                header_and_data = header + data_of_fragment
                                crc16 = GetCrc16(str(int.from_bytes(header_and_data, 'big')))
                                err_message = crc16.to_bytes(2, 'big') + header_and_data
                                # KONIEC VYTVARANIA ERR FRAGMENTU
                                # ODOSLANIE ERR FRAGMENTU CLIENTOVI
                                server_sock.sendto(err_message, client_ip_port)
                                error_results_size = len(error_results)
                            # VSETKY DAT FRAGMENTY BOLI PRIJATE NEPOSKODENE
                            elif len(error_results) == 0:
                                # VYTVARANIE ACK FRAGMENTU
                                sequence_num += 1
                                header = create_header(ACK, sequence_num, 0, 0)
                                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                                ack_message = crc16.to_bytes(2, 'big') + header
                                # KONIEC VYTVARANIA ACK FRAGMENTU
                                # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                                server_sock.sendto(ack_message, client_ip_port)
                        index += 1
                    sequence_num += 1
                output = ""
                while received_msg:
                    output += heapq.heappop(received_msg)[1].decode('utf-8')
                print("[SERVER] Prijata sprava: ", output)
                received_msg.clear()
            break

        # SPRAVA ALEBO SUBOR SU DOPOSIELANE
        # SPUSTENIE KEEP ALIVE
        print("")
        print("[SERVER] Spustam KEEP ALIVE ")
        print("")
        server_sock.settimeout(20)
        try:
            data, client_ip_port = server_sock.recvfrom(2048)
            print("[SERVER] prijimam - KEEP ALIVE")
            parsed_data = parse_data(data)
            while parsed_data['flag'] == KPA:
                # VYTVARANIE ACK FRAGMENTU NA ODPOVEDANIE CLIENTOVI, ZE INF FRAGMENT PRISIEL SPAVNE
                header = create_header(ACK, 0, 0, 0)
                crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
                ack_message = crc16.to_bytes(2, 'big') + header
                # KONIEC VYTVARANIA ACK FRAGMENTU
                server_sock.settimeout(20)
                # ODOSLANIE ACK FRAGMENTU CLIENTOVI
                print("[SERVER] posielam - ACK na KEEP ALIVE")
                server_sock.sendto(ack_message, client_ip_port)  # SERVER posiela ACK
                data, client_ip_port = server_sock.recvfrom(2048)
                print("[SERVER] prijimam - KEEP ALIVE")
                parsed_data = parse_data(data)
            if parsed_data['flag'] == INF:
                new_inf = 1
        except socket.timeout:
            print("[SERVER] KEEP ALIVE od klienta neprisiel")
            return 0


def keep_alive_client(server_ip, server_port, client_sock):
    while not terminate_event.isSet():
        event_timer = terminate_event.wait(10)
        if not event_timer:
            header = create_header(KPA, 0, 0, 0)
            crc16 = GetCrc16(str(int.from_bytes(header, 'big')))
            kpa_message = crc16.to_bytes(2, 'big') + header
            client_sock.sendto(kpa_message, (server_ip, server_port))
            try:
                data, server_ip_port = client_sock.recvfrom(SIZE_OF_HEADER + SIZE_OF_CRC)
            except socket.timeout:
                print("[KLIENT] Server pocas KEEP ALIVE neopovedal")
                terminate_event.set()
                client_sock.close()


def client(client_sock, server_ip, server_port):
    print("[KLIENT]")
    print("1 -> Sprava")
    print("2 -> Subor")
    print("3 -> Navrat do menu")
    type_of_input = int(input("Zadajte svoj vyber: "))

    terminate_event.set()

    if type_of_input == 1:  # SPRAVA
        message = input("[KLIENT] Napiste spravu: ")
        print(len(message))
        print("[KLIENT] Maximalna velkost fragmentu je 1461 [1500 - 28(IP+UDP header) - 9(hlavicka) - 2(CRC)]")
        data_size = int(input("[KLIENT] Zadajte velkost dat v Bytoch: "))
        fragment_size_client = data_size + SIZE_OF_HEADER + SIZE_OF_CRC + 15  # CLIENT moze prijat ERR packet, v ktorom bude 5 chybnych fragmentov so svojim sequence (kazdy ma 3 Byty)
        print("[KLIENT] Posielam spravu: ", message)
        client_sends_msg(data_size, fragment_size_client, server_ip, server_port, type_of_input, client_sock, message)
    elif type_of_input == 2:  # SUBOR
        file_name = "test1.txt"  # input("Zadajte nazov suboru aj s typom suboru (nazov.typ): ")
        print("[KLIENT] Maximalna velkost fragmentu je 1461 [1500 - 28(IP+UDP header) - 9(hlavicka) - 2(CRC)]")
        data_size = int(input("[KLIENT] Zadajte velkost dat v Bytoch: "))
        fragment_size_client = data_size + SIZE_OF_HEADER + SIZE_OF_CRC + 15  # CLIENT moze prijat ERR packet, v ktorom bude 5 chybnych fragmentov so svojim sequence (kazdy ma 3 Byty)
        print("[KLIENT] Posielam subor: ", file_name)
        client_sends_file(data_size, fragment_size_client, server_ip, server_port, type_of_input, client_sock, file_name)
    elif type_of_input == 3:
        return 1

    return 0

def client_prepare():
        server_ip = "localhost"  # input("Zadajte cielovu IP adresu: ")
        server_port = 5005  # int(input("Zadajte cielovy port: "))

        client_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        while True:
            returned = client(client_sock, server_ip, server_port)
            if returned == 0:
                print("")
                print("[KLIENT] spustam na pozadi KEEP ALIVE")
                print("")
                terminate_event.clear()
                thread = threading.Thread(target=keep_alive_client, args=(server_ip, server_port, client_sock))
                thread.start()

            elif returned == 1:
                client_sock.close()
                return

def server_prepare():
    server_ip = "localhost"  # input("Zadajte cielovu IP adresu: ")
    server_port = 5005  # int(input("Zadajte cielovy port: "))

    path = 'C:/Users/adamf/Desktop/PKS_files'

    server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    ip_port = (server_ip, server_port)
    server_sock.bind(ip_port)

    while True:
        returned_server = server(server_sock, path, ip_port)
        if returned_server == 1:
            return


while True:
    terminate_event.set()
    print("1 -> Klient")
    print("2 -> Server")
    option = int(input("Zadajte svoju ulohu: "))  # 1 alebo 2

    # *KLIENT*
    if option == 1:
        client_prepare()

    # *SERVER*
    elif option == 2:
        server_prepare()
