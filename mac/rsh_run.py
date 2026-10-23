#!/usr/bin/env python3
"""Run one command on the Octane as root over rsh (macOS no longer ships rsh).

    python3 -I rsh_run.py 'uname -a'

The Octane's /.rhosts must list this Mac and your user name. rshd only accepts
connections from a reserved source port; macOS lets normal users bind those
when bound to all addresses.
"""
import getpass
import socket
import sys

OCTANE = "10.10.10.203"


def connect():
    for port in range(1023, 511, -1):
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("0.0.0.0", port))
            s.settimeout(10)
            s.connect((OCTANE, 514))
            return s
        except OSError:
            s.close()
    raise SystemExit("could not connect to rshd on the Octane")


def main():
    cmd = " ".join(sys.argv[1:]) or "true"
    s = connect()
    # stderr port 0 = no separate stderr channel; then local user, remote user, command
    s.sendall(b"0\0" + getpass.getuser().encode() + b"\0root\0" + cmd.encode() + b"\0")
    status = s.recv(1)
    if status != b"\0":
        raise SystemExit("rshd refused: " + s.recv(512).decode(errors="replace").strip())
    s.settimeout(30)
    while True:
        data = s.recv(4096)
        if not data:
            break
        sys.stdout.write(data.decode(errors="replace"))


if __name__ == "__main__":
    main()
