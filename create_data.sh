mkdir -p data/from

dd if=/dev/urandom of=data/from/small.txt bs=KB count=1
dd if=/dev/urandom of=data/from/medium.txt bs=MB count=1
dd if=/dev/urandom of=data/from/large.txt bs=MB count=100
