#!/usr/bin/env bash
# 把 prototype.html 的每个页面和关键状态导出为 PNG 设计稿（2x）。
# 用法：bash export-screens.sh   （需要已安装 Google Chrome 和 python3）
set -euo pipefail
cd "$(dirname "$0")"

CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
PORT=8765
OUT=screens
mkdir -p "$OUT"

if ! curl -s "http://localhost:$PORT/prototype.html" >/dev/null; then
  python3 -m http.server "$PORT" >/dev/null 2>&1 &
  SERVER_PID=$!
  trap 'kill $SERVER_PID' EXIT
  sleep 1
fi

# 文件名|启动参数|等待毫秒
SHOTS=(
  "01-onboarding-welcome|onboarding|1200"
  "02-onboarding-folder|onboarding+o1|1200"
  "03-onboarding-preset|onboarding+o2|1200"
  "04-home|home|1200"
  "05-home-recovered|home+recover|1200"
  "06-config-by-type|config+A|1200"
  "07-config-by-type-errors|config+A+cfgerr|1200"
  "08-config-by-date|config+B|1200"
  "09-config-old-installers|config+C|1200"
  "10-config-duplicates|config+D|1200"
  "11-scan|scan+A+freeze|1200"
  "12-scan-duplicates|scan+D+freeze|1200"
  "13-preview|preview|1200"
  "14-preview-excluded-expanded|preview+excl+expand|1200"
  "15-preview-expired|preview+expired|1200"
  "16-preview-confirm|preview+m-mExec|1200"
  "17-duplicates-undecided|dup|1200"
  "18-duplicates-decided|dup+decided|1200"
  "19-executing|exec+freeze|1200"
  "20-executing-stopping|exec+stopping+freeze|1200"
  "21-result-partial|result|1200"
  "22-result-cancelled|result+cancelled|1200"
  "23-history|history|1200"
  "24-undo-preview|undo|1200"
  "25-quarantine|quar|1200"
  "26-quarantine-selected|quar+sel|1200"
  "27-quarantine-trash-confirm|quar+m-mTrash|1200"
  "28-settings|settings|1200"
  "29-about-diagnostics|about+m-mDiag|1200"
  "30-home-light|home+light|1200"
  "31-preview-light|preview+light|1200"
  "32-quarantine-light|quar+sel+light|1200"
)

for s in "${SHOTS[@]}"; do
  IFS='|' read -r name hash wait <<<"$s"
  "$CHROME" --headless=new --disable-gpu --hide-scrollbars --force-device-scale-factor=2 \
    --window-size=1280,820 --virtual-time-budget="$wait" \
    --screenshot="$PWD/$OUT/$name.png" \
    "http://localhost:$PORT/prototype.html#$hash+shot" >/dev/null 2>&1
  echo "exported $OUT/$name.png"
done
