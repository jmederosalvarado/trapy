####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

from trapy import dial, recv, send, close

conn = dial("10.0.0.1:8080")

sentence = input("enter sentence: ")
print(f"sending sentence `{sentence}`")
if sentence == "close":
    send(conn, sentence.encode())
    close(conn)
else:
    send(conn, (sentence * 1000).encode())
    print("waiting response")
    response = recv(conn, 60000)
    print(f"received `{response.decode()}`")

    close(conn)
