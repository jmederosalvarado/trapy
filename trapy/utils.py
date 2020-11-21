class ConnError(Exception):
    pass


def parse_address(address):
    host, port = address.split(":")

    if host == "":
        host = "localhost"

    return host, int(port)


class DataIdxManager(object):
    def __init__(self, initial_seq, data_len, step):
        self.map = {}
        self.step = step
        self.first, self.last = initial_seq, (initial_seq - 1) % 2 ** 32
        self.n = 0

        for i in range(initial_seq, 2 ** 32):
            if self.n == data_len + step:
                break
            self.map[i] = self.n
            self.n += 1

        for i in range(0, initial_seq):
            if self.n == data_len + step:
                break
            self.map[i] = self.n
            self.n += 1

    def map(self, seq):
        if seq == self.last:
            for _ in range(self.step):
                self.map[self.first] = self.n
                self.n += 1
                self.first = (self.first + 1) % 2 ** 32
                self.last = (self.last + 1) % 2 ** 32
        return self.map[seq]
