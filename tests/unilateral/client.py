####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import dial, send, close

conn = dial("10.0.0.1:8080")

print("sending sentence `hola`")
send(conn, ("hola" * 40).encode())

close(conn)
