import subprocess
import time

"""
This script was made because the main process gets killed after a while for
some reason. I don't know where it can borrow and not give back system
resources, all the unused file descriptors should be closed by Python when they
are cleaned by the garbage collector, and I don't think that it happens because
I do too much I/O - just one request per minute if everything is good or every
five seconds if an exception happens - not so much for a modern server, even
the weakest one (that I'm using).
"""

while True:
    subprocess.call("python3 run.py", shell=True)
    time.sleep(5)
