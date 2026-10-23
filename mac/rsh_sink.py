#!/usr/bin/env python3
"""Receive-only rsh endpoint for pulling archives off the Octane.

The IRIX miniroot has rsh but no ftp/nc, so on the Octane:
    find . -mount -print | cpio -oc | rsh 10.10.10.1 disk1.cpio
streams the archive here. This speaks just enough of the rsh protocol to
accept the connection; the "command" is only used as the output filename
(no commands are ever run). Everything received is written to
./recovered/<name>. Accepts connections only from the Octane, on en11.
No root needed (macOS lets users bind ports below 1024).
"""
import os
import re
import socket
import threading
import time

LISTEN_IP = "10.10.10.1"
OCTANE_IP = "10.10.10.203"
OUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "recovered")
REPORT_EVERY = 100 * 1024 * 1024


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def read_field(conn):
    buf = b""
    while True:
        c = conn.recv(1)
        if not c:
            raise ConnectionError("eof in handshake")
        if c == b"\0":
            return buf.decode(errors="replace")
        buf += c


def connect_back(port):
    # rcmd() insists the stderr channel comes from a reserved port.
    for local in range(1023, 511, -1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", local))
            s.connect((OCTANE_IP, port))
            return s
        except OSError:
            s.close()
    raise OSError("no reserved port for stderr channel")


def handle(conn, addr):
    err = None
    try:
        port = int(read_field(conn) or "0")
        # rcmd() waits for the stderr channel before sending the rest.
        if port:
            err = connect_back(port)
        locuser, remuser, command = (read_field(conn) for _ in range(3))
        name = re.sub(r"[^A-Za-z0-9._-]", "_", command.strip().split()[-1])
        if not name or name.startswith("."):
            conn.sendall(b"\1bad name\n")
            return
        path = os.path.join(OUT_DIR, name)
        conn.sendall(b"\0")
        log(f"{addr[0]} ({locuser}->{remuser}) receiving {path}")
        total, next_report, start = 0, REPORT_EVERY, time.time()
        with open(path, "wb") as f:
            while True:
                data = conn.recv(65536)
                if not data:
                    break
                f.write(data)
                total += len(data)
                if total >= next_report:
                    rate = total / (time.time() - start) / 1e6
                    log(f"  {name}: {total // 2**20} MB ({rate:.1f} MB/s)")
                    next_report += REPORT_EVERY
        secs = time.time() - start
        log(f"  {name}: done, {total} bytes in {secs:.0f} s")
        if err:
            err.sendall(f"received {total} bytes into {name}\n".encode())
    except Exception as e:
        log(f"{addr[0]} error: {e!r}")
    finally:
        if err:
            err.close()
        conn.close()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(("0.0.0.0", 514))  # unprivileged low ports need INADDR_ANY
    s.listen(4)
    log(f"rsh sink listening on {LISTEN_IP}:514, writing to {OUT_DIR}")
    while True:
        conn, addr = s.accept()
        if addr[0] != OCTANE_IP or addr[1] >= 1024:
            log(f"rejected {addr}")
            conn.close()
            continue
        threading.Thread(target=handle, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()
