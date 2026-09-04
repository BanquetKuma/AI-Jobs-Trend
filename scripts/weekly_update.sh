#!/usr/bin/env bash
# 毎週金曜の自動更新。Windowsタスクスケジューラから WSL 経由で呼ばれる。
#
#   schtasks /Create /TN "AI-Jobs-Trend Weekly" /SC WEEKLY /D FRI /ST 19:00 \
#     /TR "wsl.exe -d Ubuntu-24.04 -- /mnt/c/dev/AI-Jobs-Trend/scripts/weekly_update.sh"
#
# 未処理メールが無ければ何も変更せず終了するので、何度実行しても無害。
#
# 2026-09-04 の障害を受けて堅牢化した。認証が切れて3秒で落ちたが、完了メールは
# claude -p 経由のため通知手段ごと死に、誰も気づかないまま1週間分が欠測した。
# 対策として (1) OS のトースト通知を別経路で持つ (2) 終了コードを正しく返す
# (3) トークンの残り時間をログに残して原因を特定できるようにする。
set -uo pipefail

REPO=/mnt/c/dev/AI-Jobs-Trend
CLAUDE=/home/banqu/.local/bin/claude
CREDS=/home/banqu/.claude/.credentials.json
WARN_DAYS=7          # リフレッシュトークンの残りがこれ以下なら事前警告

cd "$REPO" || exit 1
mkdir -p logs
LOG="logs/weekly-$(date +%Y-%m-%d).log"
STATE="logs/.last_run"

notify() { "$REPO/scripts/notify.sh" "$1" "$2"; }

# --- 認証の残り時間を測る。失敗しても実行は止めない ---
# 今回の障害では、この情報が無かったために原因を確定できなかった。
refresh_days=$(python3 - "$CREDS" <<'PY' 2>/dev/null || echo ""
import json, sys, datetime as dt
d = json.load(open(sys.argv[1], encoding="utf-8"))["claudeAiOauth"]
now = dt.datetime.now(dt.timezone.utc).timestamp() * 1000
print(int((d["refreshTokenExpiresAt"] - now) / 86400000))
PY
)

{
  echo "=== $(date -Is) 週次更新を開始 ==="
  echo "--- 診断情報 ---"
  "$CLAUDE" --version 2>&1 | sed 's/^/claude: /'
  python3 - "$CREDS" <<'PY' 2>&1 || echo "認証情報を読めませんでした"
import json, sys, datetime as dt
d = json.load(open(sys.argv[1], encoding="utf-8"))["claudeAiOauth"]
now = dt.datetime.now(dt.timezone.utc)
for k, label in (("expiresAt", "アクセストークン"),
                 ("refreshTokenExpiresAt", "リフレッシュトークン")):
    t = dt.datetime.fromtimestamp(d[k] / 1000, dt.timezone.utc)
    h = (t - now).total_seconds() / 3600
    state = "期限切れ" if h < 0 else f"残り {h:.1f}時間"
    print(f"{label}: {state}（{t.astimezone():%Y-%m-%d %H:%M}）")
PY
  echo "----------------"
} >>"$LOG" 2>&1

# --- 前回の失敗が未解決なら知らせる ---
if [ -f "$STATE" ] && grep -q '^fail' "$STATE"; then
  notify "AI案件トレンド: 前回の更新が失敗しています" \
         "$(head -1 "$STATE") — 今回の実行で復旧を試みます"
fi

# --- リフレッシュトークンの期限が近いことを事前に知らせる ---
if [ -n "$refresh_days" ] && [ "$refresh_days" -le "$WARN_DAYS" ] 2>/dev/null; then
  if [ "$refresh_days" -lt 0 ]; then
    notify "AI案件トレンド: 認証が切れています" \
           "claude を起動して /login してください。このままでは更新できません。"
  else
    notify "AI案件トレンド: 認証の期限が近づいています" \
           "あと ${refresh_days} 日で再ログインが必要です。claude を起動して /login してください。"
  fi
fi

PROMPT='.claude/skills/ai-jobs-update/SKILL.md を読み、その手順に従って週次更新を実行してください。未処理メールが無ければ、ファイルを一切変更せずに「新着なし」と報告して終了してください。更新した場合は手順7bの完了メール送信まで実施してください。'

# 出力は一時ファイルに受ける。ログに直接追記すると、同じ日に複数回動いたときに
# 過去の実行分まで grep が拾ってしまう。
OUT=$(mktemp)
"$CLAUDE" -p "$PROMPT" \
  --allowedTools \
    "mcp__claude_ai_Gmail__search_threads" \
    "mcp__claude_ai_Gmail__get_thread" \
    "mcp__claude_ai_Gmail__send_message" \
    "Bash(python3:*)" "Bash(git:*)" "Bash(grep:*)" "Bash(ls:*)" "Bash(cat:*)" \
    "Read" "Write" "Edit" \
  < /dev/null > "$OUT" 2>&1
rc=$?

{ cat "$OUT"; echo; echo "=== $(date -Is) 終了 (exit=$rc) ==="; } >>"$LOG"

# --- 結果を判定して、失敗なら必ず人に届ける ---
if grep -qE 'Failed to authenticate|OAuth session expired|Invalid API key' "$OUT"; then
  rm -f "$OUT"
  echo "fail $(date -Is) 認証エラー" > "$STATE"
  notify "AI案件トレンド: 認証が切れています" \
         "claude を起動して /login してください。復旧後、翌日9:00の再実行で自動的に取り込まれます。"
  exit 1
fi
if [ $rc -ne 0 ]; then
  rm -f "$OUT"
  echo "fail $(date -Is) exit=$rc" > "$STATE"
  notify "AI案件トレンド: 週次更新が失敗しました" \
         "exit=$rc — $REPO/$LOG を確認してください。"
  exit "$rc"
fi

rm -f "$OUT"
echo "ok $(date -Is)" > "$STATE"
exit 0
