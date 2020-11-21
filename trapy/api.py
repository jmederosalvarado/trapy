import random
import socket
import time
from threading import Thread
import trapy.ports as port_manager
from trapy.tcp import TCPPacket
from trapy.utils import parse_address, DataIdxManager
from trapy.tasks import RecvTask


class Conn:
    def __init__(self, sock=None):
        if sock is None:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)
        self.socket = sock

        self.src_address = None
        self.dest_address = None

        self.seq_number = random.randint(0, 2 ** 32 - 1)
        self.ack_number = None

    def increase_seq_number(self):
        self.seq_number += 1
        self.seq_number %= 2 ** 32
        return self.seq_number


def listen(address: str) -> Conn:
    conn = Conn()
    conn.src_address = parse_address(address)
    port_manager.bind(conn.src_address[1])
    return conn


def accept(conn: Conn) -> Conn:
    handshake_conn = Conn()

    ## wait for syn request

    syn_packet = TCPPacket()
    while True:
        received, address = conn.socket.recvfrom(1024)
        print("received something")
        if (
            syn_packet.decode(received)
            and syn_packet.dest_port == conn.src_address[1]
            and syn_packet.syn == 1
        ):
            print("syn received")
            break

    handshake_conn.src_address = conn.src_address[0], port_manager.get_port()
    handshake_conn.dest_address = address[0], syn_packet.src_port

    ## send synack

    synack_packet = TCPPacket()
    synack_packet.src_port = handshake_conn.src_address[1]
    synack_packet.dest_port = handshake_conn.dest_address[1]
    synack_packet.syn = 1
    synack_packet.ack_number = (syn_packet.seq_number + 1) % 2 ** 32
    synack_packet.seq_number = handshake_conn.seq_number
    handshake_conn.increase_seq_number()
    handshake_conn.socket.sendto(synack_packet.encode(), handshake_conn.dest_address)

    print("synack sent")

    ## receive last segment

    last_packet = TCPPacket()
    while True:
        received, address = handshake_conn.socket.recvfrom(1024)
        if (
            last_packet.decode(received)
            and last_packet.dest_port == handshake_conn.src_address[1]
            and last_packet.syn == 0
        ):
            break

    print("last segment received")
    print("connection accepted")
    return handshake_conn


def dial(address) -> Conn:
    conn = Conn()
    conn.src_address = parse_address(f":{port_manager.get_port()}")
    server_address = parse_address(address)

    ## create and send syn packet

    syn_packet = TCPPacket()
    syn_packet.src_port = conn.src_address[1]
    syn_packet.dest_port = server_address[1]

    syn_packet.syn = 1

    syn_packet.seq_number = conn.seq_number
    ack_expected = conn.increase_seq_number()

    conn.socket.sendto(syn_packet.encode(), server_address)

    print("syn sent")

    ## receive synack packet

    synack_packet = TCPPacket()
    while True:
        packet, address = conn.socket.recvfrom(1024)
        if (
            synack_packet.decode(packet)
            and synack_packet.syn == 1
            and synack_packet.dest_port == conn.src_address[1]
            and address[0] == server_address[0]
            and ack_expected == synack_packet.ack_number
        ):
            break
    conn.dest_address = server_address[0], synack_packet.src_port
    print("synack received")

    ## send last special segment

    last_packet = TCPPacket()
    last_packet.src_port = conn.src_address[1]
    last_packet.dest_port = conn.dest_address[1]
    last_packet.syn = 0

    conn.socket.sendto(last_packet.encode(), conn.dest_address)
    print("last segment sent")


def send(conn: Conn, data: bytes) -> int:
    fragment_size = 2 ** 10
    window_start = conn.seq_number
    window_size = fragment_size * 20  # TODO: compute dynamic window size
    duplicated_ack = 0

    last_ack_time = None
    waiting_for_ack_time = 0.25
    times_waited_for_ack = 0

    data_idx_manager = DataIdxManager()

    recv_task = RecvTask()
    recv_thread = Thread(target=recv_task.recv, args=[conn])
    recv_thread.start()

    while True:
        if times_waited_for_ack > 5:
            return data_idx_manager.map(conn.seq_number)

        if last_ack_time is not None and (
            time.time() - last_ack_time
            > waiting_for_ack_time * 2 ** times_waited_for_ack
        ):
            times_waited_for_ack += 1
            last_ack_time = time.time()
            conn.seq_number = window_start

        if len(recv_task.received) > 0:
            packet = recv_task.received.popleft()  # type: TCPPacket
            print("got ack", packet.ack_number)

            if packet.ack_number != window_start:  # and ack in window
                window_start = packet.ack_number
                duplicated_ack = 0

                if (
                    conn.seq_number != window_start
                ):  # seq number is always inside window
                    last_ack_time = time.time()
                else:
                    last_ack_time = None

                if data_idx_manager.map(packet.ack_number) >= len(data):
                    recv_task.stop()
                    recv_thread.join()
                    return len(data)

            else:
                duplicated_ack += 1
                if duplicated_ack >= 3:
                    recv_task.received.clear()
                    conn.seq_number = packet.ack_number
                    duplicated_ack = 0

        if conn.seq_number < window_start + window_size and (
            data_idx_manager.map(conn.seq_number) < len(data)
        ):
            if last_ack_time is None:
                last_ack_time = time.time()

            packet_to_send = TCPPacket()
            packet_to_send.dest_port = conn.dest_address[1]
            packet_to_send.src_port = conn.src_address[1]
            packet_to_send.seq_number = conn.seq_number

            if data_idx_manager.map(conn.seq_number) + fragment_size < len(data):
                packet_to_send.data = data[
                    data_idx_manager.map(conn.seq_number) : data_idx_manager.map(
                        conn.seq_number + fragment_size
                    )
                ]

            else:
                packet_to_send.fin = 1
                packet_to_send.data = data[data_idx_manager.map(conn.seq_number) :]

            print("sent", (packet_to_send.data, conn.seq_number))
            sent_amount = conn.socket.sendto(packet_to_send.encode(), conn.dest_address)
            conn.seq_number = (conn.seq_number + sent_amount) % 2 ** 32


def recv(conn: Conn, length: int) -> bytes:
    pass


def close(conn: Conn):
    port_manager.close(conn.dest_address[1])
    conn.socket.close()
    conn.socket = None
