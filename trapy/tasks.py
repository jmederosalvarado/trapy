import socket
from queue import deque
from trapy.tcp import TCPPacket


class RecvTask:
    def __init__(self, length=1024):
        self.length = 1024
        self.is_runing = True
        self.received = deque()

    def stop(self):
        self.is_runing = False

    def recv(self, conn):
        sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_TCP)

        while self.is_runing:
            try:
                received, address = sock.recvfrom(self.length)
                packet = TCPPacket()
                if (
                    packet.decode(received)
                    and packet.dest_port == conn.src_address[1]
                    and address[0] == conn.dest_address[0]
                    and packet.src_port == conn.dest_address[1]
                ):
                    self.received.append(packet)

            except socket.timeout:
                continue

        sock.close()
