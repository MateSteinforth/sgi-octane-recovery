#!/usr/bin/env python3
"""Minimal BOOTP responder for netbooting the SGI Octane.

macOS bootpd receives the Octane PROM's BOOTP requests but never answers them,
so this replaces it: it answers only the Octane's MAC, hands out its fixed IP,
and points it at the boot file on this Mac's tftpd. Every request and reply is
logged to stdout. Needs root (UDP port 67); run start-bootp.sh rather than this.
"""
import socket
import struct
import sys
import time

IFACE = "en11"
SERVER_IP = "10.10.10.1"
CLIENT_MAC = bytes.fromhex("0800690e08c8")
CLIENT_IP = "10.10.10.203"
NETMASK = "255.0.0.0"
BOOT_FILE = sys.argv[1] if len(sys.argv) > 1 else "sa"
IP_BOUND_IF = 25  # macOS: pin the socket (and broadcasts) to one interface


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def build_reply(req, boot_file):
    xid, = struct.unpack("!I", req[4:8])
    chaddr = req[28:44]
    # Echo the file the client asked for if it named one, else use ours.
    asked = req[108:236].split(b"\0", 1)[0].decode(errors="replace")
    file_ = (asked or boot_file).encode()
    vend = bytes([99, 130, 83, 99,                # RFC 1048 magic cookie
                  1, 4]) + socket.inet_aton(NETMASK) + bytes([255])
    pkt = struct.pack("!BBBBIHH4s4s4s4s16s64s128s64s",
                      2, 1, 6, 0, xid, 0, 0,
                      req[12:16],                  # ciaddr (echo)
                      socket.inet_aton(CLIENT_IP),  # yiaddr
                      socket.inet_aton(SERVER_IP),  # siaddr = tftp server
                      b"\0" * 4,                   # giaddr
                      chaddr,
                      socket.gethostname().split(".")[0].encode()[:63],
                      file_, vend)
    return pkt, file_.decode()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    s.setsockopt(socket.IPPROTO_IP, IP_BOUND_IF, socket.if_nametoindex(IFACE))
    s.bind(("0.0.0.0", 67))
    log(f"listening on {IFACE}:67, answering {CLIENT_MAC.hex(':')} -> "
        f"{CLIENT_IP}, file {BOOT_FILE!r}, server {SERVER_IP}")
    while True:
        req, (src, sport) = s.recvfrom(1500)
        if len(req) < 236 or req[0] != 1:
            continue
        mac = req[28:34]
        asked = req[108:236].split(b"\0", 1)[0].decode(errors="replace")
        log(f"BOOTREQUEST from {mac.hex(':')} ({src}) ciaddr="
            f"{socket.inet_ntoa(req[12:16])} file={asked!r}")
        if mac != CLIENT_MAC:
            log("  not the Octane, ignored")
            continue
        reply, file_ = build_reply(req, BOOT_FILE)
        # The PROM fills in ciaddr, so per RFC 951 reply unicast to it; also
        # broadcast in case it isn't answering ARP yet.
        # The Octane resets its NIC when it starts netbooting, so en11 briefly
        # loses its address; a send can fail then, and the PROM retries in 5 s.
        ciaddr = socket.inet_ntoa(req[12:16])
        dests = ([ciaddr] if ciaddr != "0.0.0.0" else []) + ["255.255.255.255"]
        for dest in dests:
            try:
                s.sendto(reply, (dest, 68))
                log(f"  BOOTREPLY sent to {dest}: yiaddr {CLIENT_IP} "
                    f"siaddr {SERVER_IP} file {file_!r}")
            except OSError as e:
                log(f"  BOOTREPLY to {dest} failed: {e}")


if __name__ == "__main__":
    main()
