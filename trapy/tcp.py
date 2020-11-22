import socket
from struct import pack, unpack


def build_checksum(data):
    sum = 0
    for i in range(0, len(data), 2):
        if i < len(data) and (i + 1) < len(data):
            sum += data[i] + (data[i + 1]) << 8
        elif i < len(data) and (i + 1) == len(data):
            sum += data[i]
    addon_carry = (sum & 0xFFFF) + (sum >> 16)
    result = (~addon_carry) & 0xFFFF
    # swap bytes
    result = result >> 8 | ((result & 0x00FF) << 8)
    return result


def validate_checksum(ip_header, tcp_header, data=None):
    placeholder = 0
    if data is not None:
        tcp_length = 20 + len(data)
    else:
        tcp_length = 20
    protocol = ip_header[6]

    received_tcp_segment = pack(
        "!HHLLBBHHH",
        tcp_header[0],
        tcp_header[1],
        tcp_header[2],
        tcp_header[3],
        tcp_header[4],
        tcp_header[5],
        tcp_header[6],
        0,
        tcp_header[8],
    )
    pseudo_hdr = pack("!BBH", placeholder, protocol, tcp_length)
    total_msg = pseudo_hdr + received_tcp_segment
    if data is not None:
        total_msg += data

    checksum_from_packet = tcp_header[7]
    tcp_checksum = build_checksum(total_msg)

    return checksum_from_packet == tcp_checksum


class TCPPacket(object):
    def __init__(self):
        self.src_port = None
        self.dest_port = None
        self.seq_number = None
        self.ack_number = None
        self.syn = None
        self.data = None
        self.fin = None

    def encode(self):
        tcp_source = self.src_port or 0
        tcp_dest = self.dest_port or 0
        tcp_seq = self.seq_number or 0
        tcp_ack_seq = self.ack_number or 0
        tcp_doff = 5  # 4 bit field, size of tcp header, 5 * 4 = 20 bytes
        tcp_fin = self.fin or 0
        tcp_syn = self.syn or 0
        tcp_rst = 0
        tcp_psh = 0
        tcp_ack = 0
        tcp_urg = 0
        tcp_window = socket.htons(5840)  # maximum allowed window size
        tcp_check = 0
        tcp_urg_ptr = 0

        tcp_offset_res = (tcp_doff << 4) + 0
        tcp_flags = (
            tcp_fin
            + (tcp_syn << 1)
            + (tcp_rst << 2)
            + (tcp_psh << 3)
            + (tcp_ack << 4)
            + (tcp_urg << 5)
        )

        # the ! in the pack format string means network order
        tcp_header = pack(
            "!HHLLBBHHH",
            tcp_source,
            tcp_dest,
            tcp_seq,
            tcp_ack_seq,
            tcp_offset_res,
            tcp_flags,
            tcp_window,
            tcp_check,
            tcp_urg_ptr,
        )

        # pseudo header fields
        placeholder = 0
        protocol = socket.IPPROTO_TCP

        if self.data is not None:
            tcp_length = 20 + len(str(self.data))
        else:
            tcp_length = 20

        pseudo_header = pack("!BBH", placeholder, protocol, tcp_length)

        pseudo_header = pseudo_header + tcp_header
        if self.data is not None:
            pseudo_header = pseudo_header + bytes(self.data)

        tcp_check = build_checksum(pseudo_header)

        # make the tcp header again and fill the correct checksum - remember
        # checksum is NOT in network byte order
        tcp_header = pack(
            "!HHLLBBHHH",
            tcp_source,
            tcp_dest,
            tcp_seq,
            tcp_ack_seq,
            tcp_offset_res,
            tcp_flags,
            tcp_window,
            tcp_check,
            tcp_urg_ptr,
        )
        return tcp_header + (self.data if self.data else b"")

    def decode(self, encoded):
        unpacked_ip, unpacked_tcp, data = (
            unpack("!BBHHHBBH4s4s", encoded[:20]),
            unpack("!HHLLBBHHH", encoded[20:40]),
            encoded[40:],
        )

        self.src_port = unpacked_tcp[0]
        self.dest_port = unpacked_tcp[1]
        self.seq_number = unpacked_tcp[2]
        self.ack_number = unpacked_tcp[3]
        self.syn = (unpacked_tcp[5] >> 1) & 0x01
        self.fin = unpacked_tcp[5] & 0x01
        self.data = data

        # return validate_checksum(unpacked_ip, unpacked_tcp, data)
        return True
