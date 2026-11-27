#!/usr/bin/env bash
# 毎朝のログイン確認。Windowsタスクスケジューラから WSL 経由で呼ばれる。
#
#   schtasks /Create /TN "AI-Jobs-Trend AuthCheck" /SC DAILY /ST 08:00 \
#     /TR "wsl.exe -d Ubuntu-24.04 -- /mnt/c/dev/AI-Jobs-Trend/scripts/auth_check.sh"
#
# 2026-11-13〜27 に GitHub と Claude のログイン切れが金曜19時の本番で初めて
# 発覚し、公開が遅れた。切れた日のうちに Gmail で知らせ、金曜までに直せるようにする。
# 通知は Claude を経由しない notify.sh（Apps Script）なので、Claude が切れていても届く。
set -uo pipefail

REPO=/mnt/c/dev/AI-Jobs-Trend
CLAUDE=/home/banqu/.local/bin/claude
NO_PLUGINS='{"enabledPlugins":{"superpowers@claude-plugins-official":false}}'  # weekly_update.sh と同じ

cd "$REPO" || exit 1
mkdir -p logs
LOG="logs/auth-check.log"
problems=()

# --- GitHub: push の認証が通るか ---
# 公開リポジトリは読むだけなら認証が要らないので、push --dry-run で書き込み側を確かめる。
if ! out=$(GIT_TERMINAL_PROMPT=0 timeout 60 git push --dry-run origin HEAD:refs/heads/main 2>&1); then
  problems+=("GitHub: push の認証が通りません（${out:0:200}）。
  BROWSER=true gh auth login -h github.com -p https -w -s workflow でログインし直してください。")
fi

# --- Claude: 実際に1回呼んで、ログインの更新まで通るか ---
if ! out=$(timeout 180 "$CLAUDE" -p "OK とだけ返してください" --settings "$NO_PLUGINS" --max-turns 1 </dev/null 2>&1) \
   || grep -qiE 'authenticat|oauth|/login|expired' <<<"$out"; then
  problems+=("Claude: 呼び出しに失敗しました（${out:0:200}）。
  ミニPCで claude を起動して /login してください。")
fi

if [ ${#problems[@]} -eq 0 ]; then
  echo "$(date -Is) ok" >>"$LOG"
  exit 0
fi

body=$(printf '%s\n\n' "${problems[@]}")
echo "$(date -Is) fail: ${body//$'\n'/ }" >>"$LOG"
"$REPO/scripts/notify.sh" "AI案件トレンド: ログインが切れています（金曜の更新前に直してください）" \
  "$body次の金曜19時の自動更新までに直せば、欠測は出ません。" >>"$LOG" 2>&1
exit 1
