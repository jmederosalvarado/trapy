class ConnError(Exception):
    pass


def parse_address(address):
    host, port = address.split(":")

    if host == "":
        host = "localhost"

    return host, int(port)


class DataIdxMapper(object):
    def __init__(self, initial_seq, data_len, window_size, fragment_size):
        self.map = {}
        self.window_size = window_size
        self.fragment_size = fragment_size
        self.initial_seq = initial_seq
        self.last = (initial_seq + window_size - 1) % 2 ** 32
        self.n = 0

        for i in range(initial_seq, initial_seq + window_size):
            i = i % 2 ** 32
            self.map[i] = self.n
            self.n += 1

    def map_idx(self, seq):
        if (self.last >= seq and self.last - seq <= self.fragment_size) or (
            self.last < seq and ((2 ** 32 - 1) - seq + self.last) <= self.fragment_size
        ):
            for _ in range(3 * self.window_size):
                self.last = (self.last + 1) % 2 ** 32
                self.map[self.last] = self.n
                self.n += 1
                self.map.pop((self.last - 6 * self.window_size) % 2 ** 32, None)

        return self.map[seq]