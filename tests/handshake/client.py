####################################################

import sys, os

sys.path.append(os.path.abspath("."))

####################################################

# from tests.cheat_trapy import dial
from trapy import dial


conn = dial("10.0.0.1:8080")
print("handshake completed")
