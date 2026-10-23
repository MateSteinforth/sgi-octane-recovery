#!/usr/bin/env python3
"""Minimal read-only TFTP server for netbooting the SGI Octane.

macOS tftpd sends data from ephemeral ports >= 49152, which the SGI PROM's
TFTP client ignores (it only accepts source ports below 32768), so the
transfer times out. This server answers on port 69 and sends each transfer
from a port in 2048-32767. Serves files from ./tftp next to this script.
No root needed once macOS tftpd has released port 69.
"""
import os
import random
import socket
import struct
import threading
import time

IFACE = "en11"
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "tftp")
BLOCK = 512
TIMEOUT = 2.0
RETRIES = 8
IP_BOUND_IF = 25  # macOS: pin sockets to one interface

OP_RRQ, OP_DATA, OP_ACK, OP_ERROR = 1, 3, 4, 5


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def bound_socket(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(IFACE))
    s.bind(("0.0.0.0", port))
    return s


def low_port_socket():
    for _ in range(50):
        try:
            return bound_socket(random.randint(2048, 32767))
        except OSError:
            continue
    raise OSError("no free low port")


def resolve(name):
    # Clients may ask for "sa", "/sa" or a full path; serve by basename only.
    path = os.path.join(ROOT, os.path.basename(name.replace("\\", "/")))
    return path if os.path.isfile(path) else None


def send_file(client, name):
    s = low_port_socket()
    s.settimeout(TIMEOUT)
    path = resolve(name)
    if not path:
        s.sendto(struct.pack("!HH", OP_ERROR, 1) + b"File not found\0", client)
        log(f"{client[0]} RRQ {name!r}: not found")
        return
    size = os.path.getsize(path)
    log(f"{client[0]} RRQ {name!r} -> {path} ({size} bytes) from port "
        f"{s.getsockname()[1]}")
    start = time.time()
    with open(path, "rb") as f:
        block = 1
        while True:
            data = f.read(BLOCK)
            pkt = struct.pack("!HH", OP_DATA, block & 0xFFFF) + data
            for attempt in range(RETRIES):
                try:
                    s.sendto(pkt, client)
                except OSError as e:
                    # en11 briefly loses its address when the Octane resets
                    # its NIC at the start of a netboot; wait and resend.
                    log(f"  send failed ({e}), retrying")
                    time.sleep(TIMEOUT)
                    continue
                try:
                    while True:
                        ack, addr = s.recvfrom(1500)
                        if addr != client or len(ack) < 4:
                            continue
                        op, num = struct.unpack("!HH", ack[:4])
                        if op == OP_ERROR:
                            log(f"  client error: {ack[4:].rstrip(b'\0')!r}")
                            return
                        if op == OP_ACK and num == block & 0xFFFF:
                            break
                    break
                except socket.timeout:
                    continue
            else:
                log(f"  gave up at block {block} (no ACK)")
                return
            if block % 4096 == 0:
                log(f"  {block * BLOCK // 1024} KB sent")
            if len(data) < BLOCK:
                break
            block += 1
    secs = time.time() - start
    log(f"  done: {size} bytes in {secs:.1f} s")


def main():
    s = bound_socket(69)
    log(f"listening on {IFACE}:69, serving {ROOT}")
    while True:
        pkt, client = s.recvfrom(1500)
        if len(pkt) < 4 or struct.unpack("!H", pkt[:2])[0] != OP_RRQ:
            continue
        fields = pkt[2:].split(b"\0")
        name = fields[0].decode(errors="replace")
        mode = fields[1].decode(errors="replace") if len(fields) > 1 else ""
        log(f"{client[0]}:{client[1]} RRQ {name!r} mode {mode}")
        threading.Thread(target=send_file, args=(client, name), daemon=True).start()


if __name__ == "__main__":
    main()
