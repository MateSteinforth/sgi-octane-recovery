#!/bin/sh
# Swap macOS bootpd for our own BOOTP responder (bootp_server.py) on port 67.
# Ctrl-C stops it and hands port 67 back to macOS bootpd. tftpd is untouched.
# Run with sudo.
DIR=$(cd "$(dirname "$0")" && pwd)
launchctl bootout system /System/Library/LaunchDaemons/bootps.plist 2>/dev/null
pkill -x bootpd 2>/dev/null; sleep 1
tcpdump -i en11 -n -e -vv -l 'port 67 or port 68 or port 69 or arp or icmp' > "$DIR/bootp-tcpdump.txt" 2>&1 &
TP=$!
trap 'kill $TP 2>/dev/null; chmod 644 "$DIR"/bootp-*; launchctl bootstrap system /System/Library/LaunchDaemons/bootps.plist 2>/dev/null; echo "restored macOS bootpd"' EXIT
python3 -I "$DIR/bootp_server.py" "$@" 2>&1 | tee "$DIR/bootp-server.log"
