#!/usr/bin/env bash
# Install (or remove) the nightly launchd job.
#   scripts/install_nightly.sh            # install at 06:30
#   scripts/install_nightly.sh 7 15       # install at 07:15
#   scripts/install_nightly.sh --uninstall
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LABEL="com.founderos.nightly"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
DOMAIN="gui/$(id -u)"

if [[ "$(uname)" != "Darwin" ]]; then
  echo "launchd is macOS-only. On Linux, add to crontab instead:"
  echo "  30 6 * * * $ROOT/scripts/nightly.sh"
  exit 1
fi

if [[ "${1:-}" == "--uninstall" ]]; then
  launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
  rm -f "$PLIST"
  echo "Removed $LABEL"
  exit 0
fi

HOUR="${1:-6}"
MINUTE="${2:-30}"
mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/storage/logs"
sed -e "s|__ROOT__|$ROOT|g" -e "s|__HOUR__|$HOUR|g" -e "s|__MINUTE__|$MINUTE|g" \
  "$ROOT/scripts/launchd/$LABEL.plist.template" >"$PLIST"
plutil -lint "$PLIST" >/dev/null

launchctl bootout "$DOMAIN/$LABEL" 2>/dev/null || true
launchctl bootstrap "$DOMAIN" "$PLIST"
printf 'Installed %s — runs daily at %02d:%02d (or on wake if the Mac was asleep).\n' "$LABEL" "$HOUR" "$MINUTE"
echo "Run it now:   launchctl kickstart -k $DOMAIN/$LABEL"
echo "Logs:         $ROOT/storage/logs/"
