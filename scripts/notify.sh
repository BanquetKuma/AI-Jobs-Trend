#!/usr/bin/env bash
# Windows のトースト通知を出す。 notify.sh <タイトル> <本文>
#
# 週次更新の失敗を知らせるために使う。完了メールは claude -p 経由なので、
# 認証が切れると通知手段ごと死ぬ。OS 側の経路を別に持っておく必要がある。
# 通知に失敗しても本体の処理は止めない。
set -uo pipefail

TITLE="${1:-AI案件トレンド}"
BODY="${2:-}"

# PowerShell のシングルクォート文字列に入れるためのエスケープ
esc() { printf '%s' "$1" | sed "s/'/''/g"; }

powershell.exe -NoProfile -NonInteractive -Command "
\$ErrorActionPreference='Stop'
try {
  [Windows.UI.Notifications.ToastNotificationManager, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
  [Windows.UI.Notifications.ToastNotification, Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null
  [Windows.Data.Xml.Dom.XmlDocument, Windows.Data.Xml.Dom.XmlDocument, ContentType=WindowsRuntime] | Out-Null
  \$AppId = '{1AC14E77-02E7-4E5D-B744-2EB1AE5198B7}\WindowsPowerShell\v1.0\powershell.exe'
  \$tpl = [Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02)
  \$texts = \$tpl.GetElementsByTagName('text')
  \$texts.Item(0).AppendChild(\$tpl.CreateTextNode('$(esc "$TITLE")')) | Out-Null
  \$texts.Item(1).AppendChild(\$tpl.CreateTextNode('$(esc "$BODY")')) | Out-Null
  \$toast = New-Object Windows.UI.Notifications.ToastNotification \$tpl
  [Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier(\$AppId).Show(\$toast)
} catch {
  # トーストが出せない環境ではメッセージボックスに落とす
  msg.exe * /TIME:120 '$(esc "$TITLE"): $(esc "$BODY")'
}
" >/dev/null 2>&1 || true
