#!/usr/bin/env bash
# Nightly Founder OS run: back up the DB, run daily agents (plus weekly ones on
# Mondays), log everything, and raise a macOS notification if anything fails.
#
# Invoked by launchd (see scripts/install_nightly.sh); safe to run by hand.
# launchd starts jobs with a minimal environment, so this script resolves
# everything relative to the repo and never relies on your shell profile.
set -uo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT" || exit 1

PYTHON="${FOUNDER_OS_PYTHON:-$ROOT/.venv/bin/python}"
LOG_DIR="$ROOT/storage/logs"
BACKUP_DIR="$ROOT/storage/exports/nightly"
LOCK_DIR="$ROOT/storage/.nightly.lock"
KEEP_LOG_DAYS=30
KEEP_BACKUPS=7

mkdir -p "$LOG_DIR" "$BACKUP_DIR"
LOG_FILE="$LOG_DIR/nightly-$(date +%Y-%m-%d).log"
exec >>"$LOG_FILE" 2>&1

log() { printf '%s %s\n' "$(date '+%H:%M:%S')" "$*"; }

notify() {
  # Notifications only exist on macOS; elsewhere the log is the record.
  if command -v osascript >/dev/null 2>&1; then
    osascript -e "display notification \"$2\" with title \"Founder OS\" subtitle \"$1\"" || true
  fi
}

# mkdir is atomic, so it doubles as a lock that works without flock (absent on macOS).
if ! mkdir "$LOCK_DIR" 2>/dev/null; then
  if [[ -f "$LOCK_DIR/pid" ]] && kill -0 "$(cat "$LOCK_DIR/pid")" 2>/dev/null; then
    log "another run is in progress (pid $(cat "$LOCK_DIR/pid")); exiting"
    exit 0
  fi
  log "removing stale lock"
  rm -rf "$LOCK_DIR" && mkdir "$LOCK_DIR"
fi
echo $$ >"$LOCK_DIR/pid"
trap 'rm -rf "$LOCK_DIR"' EXIT

log "=== nightly run start ==="

if [[ ! -x "$PYTHON" ]]; then
  log "python not found at $PYTHON — run 'make install' first"
  notify "Nightly run failed" "Python environment missing"
  exit 1
fi

# Consistent online backup (safe even if the API has the DB open).
if [[ -f storage/founder_os.db ]]; then
  if "$PYTHON" - <<'PY'; then log "backup ok"; else log "backup FAILED (continuing)"; fi
import sqlite3, datetime, pathlib
src = sqlite3.connect("storage/founder_os.db")
dest_path = pathlib.Path("storage/exports/nightly") / f"founder_os_{datetime.date.today():%Y%m%d}.db"
dest = sqlite3.connect(dest_path)
with dest:
    src.backup(dest)
dest.close(); src.close()
PY
  # Names embed YYYYMMDD, so glob order is chronological; keep the newest N.
  backups=("$BACKUP_DIR"/founder_os_*.db)
  if (( ${#backups[@]} > KEEP_BACKUPS )); then
    rm -f "${backups[@]:0:${#backups[@]}-KEEP_BACKUPS}"
  fi
fi

status=0
"$PYTHON" workflows/run_agent.py --daily || status=1
if [[ "$(date +%u)" == "1" ]]; then
  "$PYTHON" workflows/run_agent.py --weekly || status=1
fi

find "$LOG_DIR" -name 'nightly-*.log' -mtime +"$KEEP_LOG_DAYS" -delete

if [[ $status -ne 0 ]]; then
  log "=== nightly run finished with failures ==="
  notify "Nightly run had failures" "See storage/logs/$(basename "$LOG_FILE")"
  exit 1
fi
log "=== nightly run ok ==="
