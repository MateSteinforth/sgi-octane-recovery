#!/bin/sh
# Phase 1: make this Mac a bootp + tftp server so the SGI Octane can
# network-boot SGI's standalone recovery program (sa).
# Reversible: run teardown-mac.sh to undo everything. Run with sudo.
set -e

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
SRC="$SCRIPT_DIR/tftp"
TFTP=/private/tftpboot
OCTANE_MAC="08:00:69:0e:08:c8"
OCTANE_IP="10.10.10.203"

echo "==> Copying boot files into $TFTP"
mkdir -p "$TFTP"
cp "$SRC/sa"         "$TFTP/sa"
cp "$SRC/unix.IP30"  "$TFTP/unix.IP30"
chmod 644 "$TFTP/sa" "$TFTP/unix.IP30"

echo "==> Writing /etc/bootptab"
[ -f /etc/bootptab ] && [ ! -f /etc/bootptab.pre-octane ] && cp /etc/bootptab /etc/bootptab.pre-octane
cat > /etc/bootptab <<EOF
# SGI Octane netboot recovery (added by setup-mac.sh)
%%
# hostname  hwtype  hwaddr            ipaddr        bootfile
octane      1       $OCTANE_MAC $OCTANE_IP  sa
EOF

echo "==> Enabling tftpd and bootpd"
launchctl enable system/com.apple.tftpd  2>/dev/null || true
launchctl enable system/com.apple.bootpd 2>/dev/null || true
launchctl bootstrap system /System/Library/LaunchDaemons/tftp.plist  2>/dev/null \
  || launchctl load -w /System/Library/LaunchDaemons/tftp.plist  2>/dev/null || true
launchctl bootstrap system /System/Library/LaunchDaemons/bootps.plist 2>/dev/null \
  || launchctl load -w /System/Library/LaunchDaemons/bootps.plist 2>/dev/null || true

echo "==> Done. Serving sa ($(wc -c < "$TFTP/sa" | tr -d ' ') bytes) + unix.IP30 from $TFTP"
echo "    bootptab: octane ($OCTANE_MAC) -> $OCTANE_IP, bootfile sa"
