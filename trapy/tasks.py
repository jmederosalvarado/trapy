import socket
from queue import deque
from trapy.tcp import TCPPacket


class RecvTask:
    def __init__(self):
        self.is_runing = True
        self.received = deque()

    def stop(self):
        self.is_runing = False

    def recv(self, conn):
        conn.socket.settimeout(0.1)
        while self.is_runing:
            try:
                received, address = conn.socket.recvfrom(65565)
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
