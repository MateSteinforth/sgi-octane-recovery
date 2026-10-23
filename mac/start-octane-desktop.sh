#!/bin/zsh
# One-step start of the SGI Octane's IRIX desktop in a Mac window.
# Needs only the Ethernet cable (Mac en11 10.10.10.1 <-> Octane 10.10.10.203)
# and XQuartz. Closing the "SGI Octane" window ends the desktop session.
DIR=${0:A:h}
OCTANE=10.10.10.203
X=/opt/X11/bin

echo "Checking the Octane is up..."
if ! ping -c 1 -t 3 $OCTANE >/dev/null; then
  echo "No reply from $OCTANE: is the Octane booted and the Ethernet adapter plugged in?"
  exit 1
fi

echo "Starting XQuartz..."
open -a XQuartz
for i in {1..30}; do DISPLAY=:0 $X/xdpyinfo >/dev/null 2>&1 && break; sleep 1; done

if ! DISPLAY=:2 $X/xdpyinfo >/dev/null 2>&1; then
  echo "Opening the SGI Octane window..."
  # -noreset keeps the access list when the last client disconnects
  DISPLAY=:0 nohup $X/Xephyr :2 -screen 1280x800 -listen tcp -resizeable -noreset \
    -title "SGI Octane" > "$DIR/xephyr.log" 2>&1 &
  for i in {1..15}; do DISPLAY=:2 $X/xdpyinfo >/dev/null 2>&1 && break; sleep 1; done
fi
DISPLAY=:2 $X/xhost +$OCTANE >/dev/null   # only the Octane may draw in the window

echo "Starting the IRIX desktop..."
python3 -I "$DIR/rsh_run.py" /usr/local/bin/mac-desktop
echo "Done. The desktop appears in the SGI Octane window in a few seconds."
