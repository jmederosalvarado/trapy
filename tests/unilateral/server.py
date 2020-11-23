####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import listen, accept, recv, close

conn = listen("10.0.0.1:8080")
print("---------> listening on port 8080")

client_conn = accept(conn)
print("---------> client accepted")

received = recv(client_conn, 1024)
print("---------> received", received.decode())

close(client_conn)
close(conn)
