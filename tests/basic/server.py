####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import listen, accept, recv, send, close

conn = listen("10.0.0.1:8080")
print("listening on port 8080")

while True:
    client_conn = accept(conn)
    print("client accepted")

    print("waiting sentence")
    received = recv(client_conn, 1024)
    if len(received) == 0 or received == b"close":
        close(client_conn)
        break

    decoded = received.decode()
    print(f"received `{decoded}`")

    print(f"sending `{decoded}`")
    send(client_conn, decoded.upper().encode())
    close(client_conn)

close(conn)
