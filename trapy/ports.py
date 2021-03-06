import os
import json
from trapy.utils import ConnError

current_dir = os.path.dirname(os.path.realpath(__file__))
ports_dir = f"{current_dir}/files"
ports_file = f"{ports_dir}/ports.json"


def ensure_ports_file():
    if not os.path.exists(ports_dir):
        os.mkdir(ports_dir)
    if not os.path.isfile(ports_file):
        with open(ports_file, "w") as fp:
            json.dump([], fp, ensure_ascii=False, indent=2)


def get_port():
    ensure_ports_file()

    with open(ports_file) as fp:
        busy_ports = json.load(fp)

    for port in range(int(2 ** 16)):
        if port in busy_ports:
            continue

        with open(ports_file, "w") as fp:
            json.dump(busy_ports + [port], fp=fp, ensure_ascii=False, indent=2)
        return port

    raise ConnError("no port available")


def bind(port):
    ensure_ports_file()

    with open(ports_file) as fp:
        busy_ports = json.load(fp)
    if port in busy_ports:
        raise ConnError(f"port {port} is busy")

    with open(ports_file, "w") as fp:
        json.dump(busy_ports + [port], fp=fp, ensure_ascii=False, indent=2)


def close(port):
    ensure_ports_file()

    with open(ports_file) as fp:
        busy_ports = json.load(fp)

    if port not in busy_ports:
        raise ConnError(f"port {port} is not busy")

    with open(ports_file, "w") as fp:
        json.dump(
            [p for p in busy_ports if p != port],
            fp=fp,
            ensure_ascii=False,
            indent=2,
        )
