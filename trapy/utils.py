class ConnError(Exception):
    pass


def parse_address(address):
    host, port = address.split(":")

    if host == "":
        host = "localhost"

    return host, int(port)


class DataIdxManager(object):
    def __init__(self):
        pass

    def map(self, seq_number):
        return 0
