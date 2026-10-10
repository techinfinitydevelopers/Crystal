#!/usr/bin/env bash
# Deploy only when origin/main has actually moved.
#
# Driven by a systemd timer every 5 minutes. Polling rather than a webhook on
# purpose: nothing new has to be opened to the internet, there is no shared
# secret to leak, and GitHub being unreachable just means the next tick tries
# again.
#
# To stop it deploying without disabling the timer -- during a DNS cutover, say:
#     touch /root/HOLD-DEPLOY
# and remove that file to resume.
set -euo pipefail

APP=/var/www/crystal
LOG=/var/log/crystal-autodeploy.log
HOLD=/root/HOLD-DEPLOY

exec >>"$LOG" 2>&1
stamp() { date '+%Y-%m-%d %H:%M:%S'; }

if [ -f "$HOLD" ]; then
  echo "$(stamp)  on hold ($HOLD present) - skipping"
  exit 0
fi

cd "$APP"
git fetch --depth 1 origin main -q || { echo "$(stamp)  fetch failed - will retry"; exit 0; }

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
  exit 0          # nothing new; stay quiet so the log stays readable
fi

echo "$(stamp)  new commit ${LOCAL:0:7} -> ${REMOTE:0:7}, deploying"
if /root/deploy.sh; then
  echo "$(stamp)  deployed ${REMOTE:0:7}"
else
  echo "$(stamp)  DEPLOY FAILED at ${REMOTE:0:7} - site left running on whatever was already there"
fi
