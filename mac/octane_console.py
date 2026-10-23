#!/usr/bin/env python3
"""Serial bridge for the SGI Octane console.

Everything the Octane prints is appended to octane.log (watch it with
`tail -f octane.log`). Anything written to the octane.in FIFO is sent to the
Octane, e.g.  printf 'hinv\r' > octane.in
"""
import os
import select
import sys
import termios
import time

PORT = sys.argv[1] if len(sys.argv) > 1 else "/dev/cu.usbserial-A9ZR720A"
HERE = os.path.dirname(os.path.abspath(__file__))
LOG = os.path.join(HERE, "octane.log")
FIFO = os.path.join(HERE, "octane.in")


def open_port(path):
    fd = os.open(path, os.O_RDWR | os.O_NOCTTY | os.O_NONBLOCK)
    iflag, oflag, cflag, lflag, ispeed, ospeed, cc = termios.tcgetattr(fd)
    iflag = 0
    oflag = 0
    lflag = 0
    cflag = termios.CS8 | termios.CREAD | termios.CLOCAL  # 8N1, no flow control
    cc[termios.VMIN] = 1
    cc[termios.VTIME] = 0
    termios.tcsetattr(fd, termios.TCSANOW,
                      [iflag, oflag, cflag, lflag, termios.B9600, termios.B9600, cc])
    return fd


def main():
    if not os.path.exists(FIFO):
        os.mkfifo(FIFO)
    port = open_port(PORT)
    fifo = os.open(FIFO, os.O_RDWR | os.O_NONBLOCK)  # RDWR so we never see EOF
    with open(LOG, "ab", buffering=0) as log:
        log.write(f"\n--- bridge started {time.ctime()} ---\n".encode())
        while True:
            ready, _, _ = select.select([port, fifo], [], [])
            if port in ready:
                data = os.read(port, 4096)
                if data:
                    log.write(data)
            if fifo in ready:
                data = os.read(fifo, 4096)
                for b in data:  # pace keystrokes; old consoles drop fast input
                    os.write(port, bytes([b]))
                    time.sleep(0.01)


if __name__ == "__main__":
    main()
