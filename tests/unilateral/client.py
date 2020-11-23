####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import dial, send, close

conn = dial("10.0.0.1:8080")

print("-------> sending ``")
send(conn, "".encode())
print("-------> sent ``")

close(conn)
