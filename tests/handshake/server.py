####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

# from tests.cheat_trapy import listen, accept
from trapy import listen, accept

conn = listen("10.0.0.1:8080")
client_conn = accept(conn)
print("handshake completed")
