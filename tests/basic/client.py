####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import dial, recv, send, close

conn = dial("10.0.0.1:8080")

sentence = input("enter sentence: ")
print(f"sending sentence `{sentence}`")
send(conn, sentence.encode())

response = recv(conn, 1024)
print(f"received `{response.decode()}`")

close(conn)
