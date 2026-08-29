#!/usr/bin/env bash
# 毎週金曜の自動更新。Windowsタスクスケジューラから WSL 経由で呼ばれる。
#
#   schtasks /Create /TN "AI-Jobs-Trend Weekly" /SC WEEKLY /D FRI /ST 19:00 \
#     /TR "wsl.exe -d Ubuntu-24.04 -- /mnt/c/dev/AI-Jobs-Trend/scripts/weekly_update.sh"
#
# セッションを開けっ放しにせず claude -p（ヘッドレス1回実行）で走らせる。
# 未処理メールが無ければ何も変更せず終了するので、何度実行しても無害。
set -uo pipefail

REPO=/mnt/c/dev/AI-Jobs-Trend
CLAUDE=/home/banqu/.local/bin/claude

cd "$REPO" || exit 1
mkdir -p logs
LOG="logs/weekly-$(date +%Y-%m-%d).log"

PROMPT='.claude/skills/ai-jobs-update/SKILL.md を読み、その手順に従って週次更新を実行してください。未処理メールが無ければ、ファイルを一切変更せずに「新着なし」と報告して終了してください。更新した場合は手順7bの完了メール送信まで実施してください。'

{
  echo "=== $(date -Is) 週次更新を開始 ==="
  # スキル名ではなく SKILL.md のパスを直接渡す。スキル探索の可否に依存させない。
  # cd 済みなので claude 側で cd は不要（Bash(python3:*) は複合コマンドにマッチしないため）。
  "$CLAUDE" -p "$PROMPT" \
    --allowedTools \
      "mcp__claude_ai_Gmail__search_threads" \
      "mcp__claude_ai_Gmail__get_thread" \
      "mcp__claude_ai_Gmail__send_message" \
      "Bash(python3:*)" "Bash(git:*)" "Bash(grep:*)" "Bash(ls:*)" \
      "Read" "Write" "Edit" \
    < /dev/null
  rc=$?
  echo
  echo "=== $(date -Is) 終了 (exit=$rc) ==="
} >>"$LOG" 2>&1
