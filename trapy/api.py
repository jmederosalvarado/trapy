import random
import socket
import time
from threading import Thread
import trapy.ports as port_manager
from trapy.tcp import TCPPacket
from trapy.utils import parse_address, DataIdxMapper
from trapy.tasks import RecvTask


class Conn:
    def __init__(self, sock=None):
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.socket = sock

        self.src_address = None
        self.dest_address = None

        self.seq_number = random.randint(0, 2 ** 32 - 1)
        self.expected_seq_number = None

        self.pending_received = b""

        # self.socket.settimeout(1)


def listen(address: str) -> Conn:
    conn = Conn()
    conn.src_address = parse_address(address)
    port_manager.bind(conn.src_address[1])
    return conn


def __handshake(conn, handshake_conn, syn_packet):

    ## create synack

    synack_packet = TCPPacket()
    synack_packet.src_port = handshake_conn.src_address[1]
    synack_packet.dest_port = handshake_conn.dest_address[1]
    synack_packet.syn = 1
    synack_packet.ack_number = (syn_packet.seq_number + 1) % 2 ** 32
    synack_packet.is_ack = 1
    synack_packet.seq_number = handshake_conn.seq_number

    handshake_conn.seq_number = (handshake_conn.seq_number + 1) % 2 ** 32
    handshake_conn.expected_seq_number = synack_packet.ack_number

    ## send synack and wait last segment

    last_packet = TCPPacket()
    times_waited_last_segment = 0

    while True:
        handshake_conn.socket.sendto(
            synack_packet.encode(), handshake_conn.dest_address
        )
        print("synack sent")

        handshake_conn.socket.settimeout(0.25 * 2 ** times_waited_last_segment)
        try:
            received, address = handshake_conn.socket.recvfrom(1024)
            if (
                last_packet.decode(received)
                and last_packet.dest_port == handshake_conn.src_address[1]
                and last_packet.syn == 0
            ):
                handshake_conn.socket.settimeout(None)
                print("last segment received")
                return True

        except socket.timeout:
            times_waited_last_segment += 1
            if times_waited_last_segment >= 5:
                handshake_conn.socket.settimeout(None)
                print("timeout ignoring syn client")
                return False


def accept(conn: Conn) -> Conn:
    handshake_conn = Conn()

    ## wait for syn request

    syn_packet = TCPPacket()
    while True:
        received, address = conn.socket.recvfrom(1024)
        if (
            not syn_packet.decode(received)
            or syn_packet.dest_port != conn.src_address[1]
            or syn_packet.syn != 1
        ):
            continue

        print("syn received")

        handshake_conn.src_address = conn.src_address[0], port_manager.get_port()
        handshake_conn.dest_address = address[0], syn_packet.src_port
        if __handshake(conn, handshake_conn, syn_packet):
            break

    print("connection accepted")
    return handshake_conn


def dial(address) -> Conn:
    conn = Conn()
    conn.src_address = parse_address(f":{port_manager.get_port()}")
    server_address = parse_address(address)

    ## create syn packet

    syn_packet = TCPPacket()
    syn_packet.src_port = conn.src_address[1]
    syn_packet.dest_port = server_address[1]
    syn_packet.syn = 1
    syn_packet.seq_number = conn.seq_number

    conn.seq_number = (conn.seq_number + 1) % 2 ** 32
    ack_expected = conn.seq_number

    ## send syn packet and wait synack

    synack_packet = TCPPacket()
    times_waited_synack = 0

    while True:
        conn.socket.sendto(syn_packet.encode(), server_address)
        print("syn sent")

        conn.socket.settimeout(0.25 * 2 ** times_waited_synack)
        try:
            packet, address = conn.socket.recvfrom(1024)
            if (
                synack_packet.decode(packet)
                and synack_packet.syn == 1
                and synack_packet.dest_port == conn.src_address[1]
                and address[0] == server_address[0]
                and ack_expected == synack_packet.ack_number
            ):
                break
        except socket.timeout:
            times_waited_synack += 1

    conn.socket.settimeout(None)
    conn.dest_address = server_address[0], synack_packet.src_port
    conn.expected_seq_number = (synack_packet.seq_number + 1) % 2 ** 32
    print("synack received")

    ## send last special segment

    last_packet = TCPPacket()
    last_packet.src_port = conn.src_address[1]
    last_packet.dest_port = conn.dest_address[1]
    last_packet.syn = 0

    conn.socket.sendto(last_packet.encode(), conn.dest_address)
    print("last segment sent")

    return conn


def send(conn: Conn, data: bytes) -> int:
    print("enter send")

    fragment_size = 2 ** 10
    window_start = conn.seq_number
    window_size = fragment_size * 20  # TODO: compute dynamic window size
    duplicated_ack = 0

    last_ack_time = None
    waiting_for_ack_time = 0.25
    times_waited_for_ack = 0

    mapper = DataIdxMapper(conn.seq_number, len(data), window_size, fragment_size)

    recv_task = RecvTask()
    recv_thread = Thread(target=recv_task.recv, args=[conn])
    recv_thread.start()

    while True:
        # if times_waited_for_ack > 5:
        #     print("max number of retries exceeded")
        #     recv_task.stop()
        #     recv_thread.join()
        #     return mapper.map_idx(window_start)

        if last_ack_time is not None and (
            time.time() - last_ack_time
            > waiting_for_ack_time * 2 ** times_waited_for_ack
        ):
            times_waited_for_ack += 1
            last_ack_time = time.time()
            conn.seq_number = window_start

        if len(recv_task.received) > 0:
            packet = recv_task.received.popleft()  # type: TCPPacket

            if packet.is_ack != 1:
                print("got packet that is not ack")
                continue

            print("got ack", packet.ack_number)

            if mapper.map_idx(packet.ack_number) > mapper.map_idx(window_start):
                window_start = packet.ack_number
                duplicated_ack = 0

                if mapper.map_idx(conn.seq_number) > mapper.map_idx(window_start):
                    last_ack_time = time.time()
                else:
                    last_ack_time = None

                if mapper.map_idx(packet.ack_number) >= len(data):
                    print("got all acks")
                    recv_task.stop()
                    recv_thread.join()
                    return len(data)

            else:
                duplicated_ack += 1
                if duplicated_ack >= 3:
                    recv_task.received.clear()
                    conn.seq_number = packet.ack_number
                    duplicated_ack = 0

        if mapper.map_idx(conn.seq_number) < len(data) and (
            mapper.map_idx(conn.seq_number) < mapper.map_idx(window_start) + window_size
        ):
            if last_ack_time is None:
                last_ack_time = time.time()

            packet_to_send = TCPPacket()
            packet_to_send.dest_port = conn.dest_address[1]
            packet_to_send.src_port = conn.src_address[1]
            packet_to_send.seq_number = conn.seq_number

            if mapper.map_idx(conn.seq_number) + fragment_size < len(data):
                packet_to_send.data = data[
                    mapper.map_idx(conn.seq_number) : mapper.map_idx(
                        conn.seq_number + fragment_size
                    )
                ]

            else:
                packet_to_send.fin = 1
                packet_to_send.data = data[mapper.map_idx(conn.seq_number) :]

            print("sent seq", conn.seq_number)
            sent_amount = conn.socket.sendto(packet_to_send.encode(), conn.dest_address)
            conn.seq_number = (conn.seq_number + sent_amount) % 2 ** 32


def recv(conn: Conn, length: int) -> bytes:
    print("enter recv")

    received = conn.pending_received
    conn.pending_received = b""

    last_packet_time = None
    waiting_for_packet_time = 0.25
    times_waited_for_packet = 0

    recv_task = RecvTask(length)
    recv_thread = Thread(target=recv_task.recv, args=[conn])
    recv_thread.start()

    duplicated_ack_sent = 0

    while True:
        if len(received) >= length:
            print(f"received {length} bytes")
            recv_task.is_runing = False
            recv_thread.join()
            conn.pending_received = received[length:]
            return received[:length]

        # if times_waited_for_packet > 5:
        #     print("max retries waiting for packet")
        #     recv_task.stop()
        #     recv_thread.join()
        #     return received

        ack_packet = TCPPacket()
        ack_packet.src_port = conn.src_address[1]
        ack_packet.dest_port = conn.dest_address[1]
        ack_packet.is_ack = 1

        if last_packet_time is not None and (
            time.time() - last_packet_time
            > waiting_for_packet_time * 2 ** times_waited_for_packet
        ):
            print("timeout waiting for packet")
            last_packet_time = time.time()
            times_waited_for_packet += 1
            ack_packet.ack_number = conn.expected_seq_number
            print("resent ack", ack_packet.ack_number)
            conn.socket.sendto(ack_packet.encode(), conn.dest_address)

        if len(recv_task.received) > 0:
            packet = recv_task.received.popleft()  # type: TCPPacket
            last_packet_time = time.time()

            if packet.is_ack:
                continue

            print("got seq", packet.seq_number)

            if packet.seq_number == conn.expected_seq_number:
                received += packet.data
                times_waited_for_packet = 0
                duplicated_ack_sent = 0
                conn.expected_seq_number = (
                    packet.seq_number + len(packet.data)
                ) % 2 ** 32

                ack_packet.ack_number = conn.expected_seq_number

                print("sent ack", ack_packet.ack_number)
                conn.socket.sendto(ack_packet.encode(), conn.dest_address)
                if packet.fin == 1:
                    print("received last packet")
                    recv_task.is_runing = False
                    recv_thread.join()
                    if len(received) > length:
                        conn.pending_received = received[length:]
                        received = received[:length]
                    return received

            else:
                print("expected seq", conn.expected_seq_number)
                duplicated_ack_sent += 1
                if duplicated_ack_sent >= 3:
                    recv_task.received.clear()
                    duplicated_ack_sent = 0
                ack_packet.ack_number = conn.expected_seq_number
                print("resent ack", ack_packet.ack_number)
                conn.socket.sendto(ack_packet.encode(), conn.dest_address)


def close(conn: Conn):
    port_manager.close(conn.src_address[1])
    conn.socket.close()
    conn.socket = None
