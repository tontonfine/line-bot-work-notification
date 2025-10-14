# 🚀 クイックスタートガイド

このガイドに従って、最短5分でシステムを起動できます。

## ⚡ 最短セットアップ（5分）

### 1. LINE Developers 設定（3分）

#### Messaging API チャネル作成
1. https://developers.line.biz/console/ にアクセス
2. 「新規チャネル作成」→「Messaging API」を選択
3. 必要事項を入力して作成

#### 必要な情報を取得
```
✓ Channel Access Token (長期)
  → 「Messaging API設定」タブ → 一番下の「チャネルアクセストークン」

✓ Channel Secret
  → 「チャネル基本設定」タブ → チャネルシークレット

✓ LIFF ID（後で設定）
```

### 2. アプリケーションセットアップ（2分）

```bash
# 1. セットアップスクリプト実行
./setup.sh

# 2. 環境変数を設定
nano .env

# 以下を貼り付け（値は自分のものに置き換え）
LINE_CHANNEL_ACCESS_TOKEN=取得したトークン
LINE_CHANNEL_SECRET=取得したシークレット
LIFF_ID=後で設定
SECRET_KEY=ランダムな文字列

# 3. アプリ起動
source venv/bin/activate
python app.py
```

### 3. LIFF設定（開発環境用）

```bash
# 別ターミナルで ngrok 起動
ngrok http 5000
# → https://abcd1234.ngrok.io のようなURLが表示される
```

LINE Developers Console に戻って：
1. 「LIFF」タブ → 「追加」
2. 設定：
   - エンドポイントURL: `https://abcd1234.ngrok.io/register`
   - サイズ: Full
   - Scope: profile, openid にチェック
3. 作成後、LIFF IDをコピーして `.env` に追加

### 4. 動作確認

1. ブラウザで `http://127.0.0.1:5000` を開く
2. 従業員管理画面で従業員を追加
3. スマホでLINE公式アカウントを友だち追加
4. LIFF URL（`https://liff.line.me/あなたのLIFF_ID`）を開いて登録
5. 送信画面から勤務連絡を送信

## 🎯 最小限の初回テスト

### テスト用従業員を1名追加

```bash
# データベースに直接追加
sqlite3 database.db
INSERT INTO employees (name, employee_number) VALUES ('テスト太郎', 'TEST001');
.exit
```

### アプリ起動して確認

```bash
python app.py
```

ブラウザで http://127.0.0.1:5000 を開いて画面が表示されればOK

## 📱 LIFF なしで動作確認（オプション）

LIFFの設定が面倒な場合は、直接LINE User IDを設定：

```bash
sqlite3 database.db
# 自分のLINE User IDを取得（LINE Botに話しかけてログから確認）
UPDATE employees SET line_user_id = 'Uxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx' WHERE employee_number = 'TEST001';
.exit
```

これで送信テストができます。

## 🔧 よくある問題

### `ModuleNotFoundError: No module named 'flask'`
```bash
# 仮想環境を有効化し忘れている
source venv/bin/activate
pip install -r requirements.txt
```

### `sqlite3.OperationalError: no such table: employees`
```bash
# データベース初期化
python database.py
```

### 送信しても届かない
1. `.env` のトークンが正しいか確認
2. LINE Developers Console で Messaging API が有効か確認
3. 従業員の `line_user_id` が登録されているか確認

## 📚 次のステップ

- [README.md](README.md) で詳細な使い方を確認
- 従業員を追加して実際に送信テスト
- メッセージフォーマットをカスタマイズ
- 本番環境へのデプロイ

## 💡 開発のヒント

### リアルタイムでコード変更を反映
```bash
# Flaskのdebugモードで起動（デフォルト有効）
python app.py
# コードを変更すると自動で再起動される
```

### データベースの中身を確認
```bash
sqlite3 database.db
.tables  # テーブル一覧
SELECT * FROM employees;  # 全従業員を表示
.exit
```

### ログを確認
ターミナルに表示される送信ログを確認：
```
✅ 送信成功: 2024年1月15日 東京オフィス 9:00 お願いします
❌ 送信失敗: 401 - Invalid access token
```
