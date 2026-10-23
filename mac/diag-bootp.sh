#!/bin/sh
# Diagnose why bootpd doesn't answer the Octane: runs bootpd in the foreground
# with verbose logging plus a packet capture for 60 s, then hands bootpd back
# to launchd. Output: ~/octane-recovery/diag-*.txt. Run with sudo.
OUT=$(cd "$(dirname "$0")" && pwd)
launchctl bootout system /System/Library/LaunchDaemons/bootps.plist 2>/dev/null
pkill -x bootpd 2>/dev/null; sleep 1
tcpdump -i en11 -n -e -vvv -s 0 'port 67 or port 68 or port 69 or arp' > "$OUT/diag-tcpdump.txt" 2>&1 &
TP=$!
/usr/libexec/bootpd -d -v > "$OUT/diag-bootpd.txt" 2>&1 &
BP=$!
echo "Capturing for 60 s (Claude will trigger the boot now)..."
sleep 60
kill $TP $BP 2>/dev/null; sleep 1
launchctl bootstrap system /System/Library/LaunchDaemons/bootps.plist 2>/dev/null
chmod 644 "$OUT"/diag-*.txt
echo "DIAG DONE"
