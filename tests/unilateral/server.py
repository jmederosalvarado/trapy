####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import listen, accept, recv, close

conn = listen("10.0.0.1:8080")
print("---------> listening on port 8080")

client_conn = accept(conn)
print("---------> client accepted")

len_received = 0
while len_received <= 40:
    received = recv(client_conn, 4)
    print("---------> received", received.decode())
    len_received += len(received)

close(client_conn)
close(conn)
