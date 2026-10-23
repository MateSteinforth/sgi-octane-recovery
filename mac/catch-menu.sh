#!/bin/zsh
# Catch the Octane PROM at startup and stop it at the System Maintenance Menu.
cd "${0:A:h}"
start=$(wc -c < octane.log)
for i in {1..1200}; do
  new=$(tail -c +$((start + 1)) octane.log 2>/dev/null)
  case "$new" in
    *"Option?"*) echo "MENU REACHED"; exit 0 ;;
  esac
  case "$new" in
    *"Starting up the system"*|*"To perform system maintenance"*) printf '\033' > octane.in ;;
    *"Press any key"*) printf '\r' > octane.in ;;
  esac
  sleep 1
done
echo "timed out"; exit 1
