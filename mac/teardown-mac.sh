#!/bin/sh
# Undo setup-mac.sh: stop bootpd + tftpd, remove boot files and bootptab entry.
# Run with sudo.
TFTP=/private/tftpboot
echo "==> Stopping bootpd and tftpd"
launchctl bootout system/com.apple.bootpd 2>/dev/null || launchctl unload -w /System/Library/LaunchDaemons/bootps.plist 2>/dev/null || true
launchctl bootout system/com.apple.tftpd  2>/dev/null || launchctl unload -w /System/Library/LaunchDaemons/tftp.plist  2>/dev/null || true
launchctl disable system/com.apple.bootpd 2>/dev/null || true
launchctl disable system/com.apple.tftpd  2>/dev/null || true
echo "==> Removing boot files"
rm -f "$TFTP/sa" "$TFTP/unix.IP30"
echo "==> Restoring /etc/bootptab"
if [ -f /etc/bootptab.pre-octane ]; then mv /etc/bootptab.pre-octane /etc/bootptab; else rm -f /etc/bootptab; fi
echo "==> Teardown complete."
