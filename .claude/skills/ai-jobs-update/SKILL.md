---
name: ai-jobs-update
description: エッジテクノロジーの週次AI案件メールを取り込み、トレンドJSONを再生成してGitHub Pagesへpushする。未処理メールが無ければ何もしない。/loop から定期実行する用途。
---

# AI案件トレンド 週次更新

毎週金曜 18:00 JST 前後に `coordinator@edge-tech.co.jp` から届く案件メールを取り込み、
ダッシュボード (https://banquetkuma.github.io/AI-Jobs-Trend/) を更新する。

**冪等**に作ってある。未処理メールが無ければ何も変更せず終了すること。
これが停止条件であり、`/loop` から高頻度で叩かれても無害である前提を壊さないこと。

作業ディレクトリは `/mnt/c/dev/AI-Jobs-Trend`。

## 手順

### 1. 処理済み台帳を読む

```bash
python3 -c "
import json; print('\n'.join(json.load(open('data/state.json'))['processed']))" | tail -5
```

`processed` の各要素は `<受信日>_<threadId>` 形式。

### 2. 未処理メールを洗い出す

`mcp__claude_ai_Gmail__search_threads` を次のクエリで呼ぶ:

- `query`: `from:coordinator@edge-tech.co.jp subject:案件 newer_than:60d`
- `view`: `THREAD_VIEW_MINIMAL`
- `pageSize`: `20`

返ってきた各スレッドについて `<date>_<threadId>`（`date` は `date` フィールドの YYYY-MM-DD 部分）
を作り、`processed` に無いものだけを対象にする。

### 3. 未処理が0件なら、ここで終了する

ファイルを触らない。commit もしない。「新着なし」とだけ報告する。
**これが通常の tick の挙動**であり、正常な結果である。

### 4. 未処理メールを取得して保存する

各未処理スレッドについて:

1. `mcp__claude_ai_Gmail__get_thread` を `threadId` と `messageFormat: "PLAIN_TEXT"` で呼ぶ
2. `sender` が `coordinator@edge-tech.co.jp` のメッセージを選ぶ
3. `plaintextBody` を **一字一句そのまま** `data/raw/<date>_<threadId>.txt` に保存する
4. **保存したら必ず検算する:**

   ```bash
   grep -o "案件番号 [0-9]" data/raw/<date>_<threadId>.txt | wc -l
   ```

   1以上なら正常。**0 だったら手順5へ。**

### 4b. `PLAIN_TEXT` が空テンプレートを返したとき

このメールは配信時期によって `text/plain` パートが
`案件番号 【案件名：】` だけの**空テンプレート（約1,469バイト）**になっていることがあり、
実際の案件一覧は `text/html` パートにしか存在しない。
`plaintextBody` をそのまま保存すると、**エラーも警告も出ないまま中身ゼロのファイルができる**。
2025年前半の配信分は全滅していた実績がある。

手順4の検算が 0 だったら、そのファイルを削除して取り直す:

1. `get_thread` を **`messageFormat: "FULL_CONTENT"`** で呼び直す
2. `plaintext_body` ではなく **`html_body`** を使う
3. テキスト化する: `<br>` `<br/>` `</p>` `</tr>` `</div>` `</td>` を改行に置換 →
   残りのHTMLタグを除去 → 実体参照を復元（`&amp;` `&lt;` `&gt;` `&quot;` `&#39;` `&nbsp;`）
4. 保存して、手順4の検算をもう一度通す

本文に `案件番号 <数字>` が1件も無いメール（年末挨拶・状況確認フォーム等）は保存せずスキップしてよい。
`build.py` は案件ゼロの生ファイルを取り込まず `WARNING` を出し、`state.json` にも記録しない
（＝次回また取得を試みる）ので、放置しても静かに欠測することはない。

**整形・要約・省略は禁止**。`===` 区切り線、`案件番号 NNNNN`、`[必須スキル]：` のような
全角スペース入りラベルはすべてパーサが依存している。

### 4c. Gmail の呼び出しがブロックされたら

権限分類器が Gmail の呼び出しを断続的にブロックすることがある。
**同じ呼び出しをそのまま2回まで再試行する**（多くはこれで通る）。
3回失敗したらその日付を未処理のまま残し、ユーザーに報告する。回避策は探さない。

### 5. 集計を再生成する

```bash
cd /mnt/c/dev/AI-Jobs-Trend && python3 scripts/build.py
```

標準出力の `weeks` と `top10` に目を通し、週数が1つ増えていることを確認する。
`raw files parsed` が 0 のときは保存に失敗しているので、4に戻る。
**stderr に `WARNING: 案件が1件も取れなかった生メールファイル` が出たら、
そこに挙がったファイルは 4b の手順で取り直す。**

### 6. 今週の所感を書く

`docs/data/summary.json` を読み、最新週の数字（`latest`, `top_techs`, `rising`,
`distributions.*_latest`）と、`docs/data/weeks/<latest_week>.json` の案件を見て、
`commentary` フィールドを埋める。以下を意識する:

- 前週・直近数週と比べて何が動いたか（伸びた技術／落ちた技術）
- 今週の新規案件に共通する傾向（業界、ポジション、稼働形態）
- 単なる件数の言い換えではなく、読み手が「市場で何が起きているか」を掴める一文を入れる

**書式の規約（サイトとメールの両方がこの記法を解釈する）:**

- **3〜4段落に分ける。段落の区切りは空行（`\n\n`）。** 1本の長い塊にしない。
  1段落＝1つの論点にする。目安は次の構成:
  1. 今週の規模（件数・新規率）
  2. 直近数週で伸びた技術／落ちた技術
  3. 今週いちばん目を引いた動きと、その意味
  4. 業界・ポジションの構成
- **重要な箇所を `**…**` で囲む。** サイトでもメールでも太字＋緑で表示される。
  **1段落あたり1〜2箇所まで。** 囲みすぎると強調が効かなくなる。
  囲む対象は「数字そのもの」ではなく、**読み手の判断を変える事実**にする
  （例: `**AIコーディング支援の0→4**`、`**全件が今週初出の新規案件**`）
- HTMLタグは書かない。`**` と空行だけを使う

事実に基づくこと。データにない推測（企業名、受注額、業界動向の憶測）は書かない。
`commentary` は次回 build でも保持されるので、毎回上書きしてよい。

### 7. コミットして push する

```bash
cd /mnt/c/dev/AI-Jobs-Trend && git status --short && git diff --stat
```

差分が無ければ何もしない。差分があれば:

```bash
git add -A && git commit -m "chore: 案件トレンド更新 <最新週の日付>" && git push
```

push が GitHub Pages の再デプロイを兼ねる（Actions は使っていない）。

### 7b. 完了メールを送る

**この手順は、7 で実際に commit と push が走ったときだけ実行する。**
差分が無く「新着なし」で終わった回では送らない
（金曜と土曜の予備実行で、毎週2通の無意味な通知が届くことになるため）。

`mcp__claude_ai_Gmail__send_message` を次の内容で呼ぶ。

- `to`: **リポジトリには書かない。** 次のコマンドで宛先を読む:
  ```bash
  cat ~/.config/ai-jobs-trend/notify_to
  ```
  ファイルが無い、または空の場合は**メールを送らず**、その旨を報告して終了する
  （更新自体は成功しているので失敗扱いにしない）
- `subject`: `【エッジテクノロジー】AI案件トレンド <最新週の日付> 配信分を反映しました`
  （配信元がひと目で分かるよう、冒頭にエッジテクノロジーを冠する）
- **`htmlBody` を必ず使う。** プレーンテキストの `body` だけで送ると、Gmail が本文中の
  裸URLを自動リンク化する際に `google.com/url?q=...` を挟み、クリック時に
  「Redirect Notice」の中間ページが出る。`<a href="...">` として渡せばこれを回避できる。
  `body` にはプレーンテキスト版を入れておく（HTMLを表示しないクライアント向けの代替）。

`htmlBody` の形（インラインスタイルのみ。外部CSSはメールクライアントで効かない）:

```html
<div style="font-family:-apple-system,'Hiragino Kaku Gothic ProN',Meiryo,sans-serif;font-size:15px;line-height:1.8;color:#1a1a1a;max-width:640px">
  <p style="margin:0 0 10px">
    <a href="https://banquetkuma.github.io/AI-Jobs-Trend/"
       style="display:inline-block;background:#1d6b46;color:#ffffff;text-decoration:none;padding:11px 22px;border-radius:3px;font-weight:700">
      ダッシュボードを開く</a>
  </p>
  <!-- Gmailウェブ版はリンクを google.com/url?q=... に書き換えるため、自己宛メールでは
       署名が付かず「Redirect Notice」の中間ページが出る。書き方では防げないので、
       コピーして使える素のURLを必ず併記する。掲載するのは必ずトップページのURL。 -->
  <p style="margin:0 0 24px;font-size:12.5px;color:#888;border:1px dashed #ccc;padding:8px 12px;border-radius:3px">
    中間ページが出る場合はこちらをコピーしてアドレスバーへ:<br>
    <span style="font-family:ui-monospace,Menlo,monospace;font-size:13px;color:#1a1a1a;user-select:all">https://banquetkuma.github.io/AI-Jobs-Trend/</span>
  </p>
  <h3 style="margin:22px 0 6px;font-size:14px;color:#1d6b46">今回取り込んだ週</h3>
  <p style="margin:0">&lt;latest_week&gt;（掲載 &lt;latest.projects&gt; 件 / うち新規 &lt;latest.new_projects&gt; 件）</p>
  <h3 style="margin:22px 0 6px;font-size:14px;color:#1d6b46">累計</h3>
  <p style="margin:0">&lt;totals.weeks&gt; 週分 / 延べ &lt;totals.listings&gt; 件 / ユニーク &lt;totals.unique_projects&gt; 件</p>
  <h3 style="margin:22px 0 6px;font-size:14px;color:#1d6b46">今週の所感</h3>
  <!-- commentary は空行で段落に割り、**…** を <strong> に変換して入れる -->
  <p style="margin:0 0 1.1em">&lt;段落1&gt;</p>
  <p style="margin:0 0 1.1em">&lt;段落2&gt;</p>
  <h3 style="margin:22px 0 6px;font-size:14px;color:#1d6b46">次に取るべき技術</h3>
  <ol style="margin:0;padding-left:20px">
    <li>&lt;name&gt;（直近&lt;window&gt;週 &lt;recent&gt;件 / 成長 &lt;growth_pct&gt;）</li>
  </ol>
  <p style="margin:26px 0 0;font-size:13px;color:#666">
    <a href="https://banquetkuma.github.io/AI-Jobs-Trend/trends.html" style="color:#1d6b46">トレンド分析ページ</a>
  </p>
</div>
```

**数字はすべて `docs/data/summary.json` と `docs/data/strategy.json` の実値を使い、創作しない。**

**所感の変換規則:**
- `commentary` を空行で分割し、各段落を `<p style="margin:0 0 1.1em">` で包む
- 段落内の `**…**` を
  `<strong style="color:#1d6b46;font-weight:700">…</strong>` に置換する
- `body`（プレーンテキスト版）では `**` を取り除き、段落間は空行1つで区切る

GitHub Pages の再デプロイには push から1〜2分かかるが、**メール送信は push 直後でよく、
デプロイ完了を待つ必要はない。**

送信に失敗しても、更新自体は成功している。**リトライせず**にその旨を報告して終了する。

### 8. 報告

1〜2文で「どの週を取り込み、案件が何件（うち新規何件）で、何が伸びたか」を報告する。
新着が無かった場合は「新着なし」の一言でよい。

## 守ること

- `data/raw/` は `.gitignore` 済み。**生のメール本文を絶対にコミットしない**。
  コミット前に `git diff --cached --name-only` に `data/raw/` が出ていないことを確認する。
- 公開してよいのは匿名化済みの集計値のみ。`data/projects.jsonl` は案件番号のSHA1先頭12桁と
  ポジション・業界・稼働形態・単価・技術タグだけを持つ。ここに本文やタイトルを足さないこと。
- 技術辞書に無い新しい技術名を案件本文で見かけたら、`scripts/tech_dict.py` に追記して
  build をやり直してよい。追記したら理由をコミットメッセージに書くこと。
