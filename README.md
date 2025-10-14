# 📱 LINE勤務連絡一斉送信システム

LINE公式アカウントから複数の従業員に勤務連絡を一斉送信できるWebアプリケーション

## ✨ 主な機能

- 📤 **一斉送信**: 複数の従業員に勤務連絡を一括送信
- 👥 **従業員管理**: 従業員情報をデータベースで管理
- 🔗 **LIFF連携**: 従業員がLINEアプリから簡単に登録
- 📊 **送信履歴**: 過去の送信記録を確認
- 📍 **勤務場所管理**: 複数の勤務場所を設定可能
- ⏰ **個別カスタマイズ**: 各従業員ごとに日時・場所を調整可能

## 🛠️ 技術スタック

- **バックエンド**: Python 3.9+, Flask
- **データベース**: SQLite
- **フロントエンド**: HTML, Bootstrap 5, JavaScript
- **LINE連携**: LINE Messaging API, LIFF

## 📋 必要な準備

### 1. LINE Developers アカウント設定

1. [LINE Developers Console](https://developers.line.biz/console/) にログイン
2. 新規プロバイダーを作成（既存でも可）
3. Messaging APIチャネルを作成
4. 以下の情報を取得：
   - **Channel Access Token** (長期)
   - **Channel Secret**

### 2. LIFF アプリ設定

1. 作成したチャネルの「LIFF」タブを開く
2. 「追加」ボタンをクリック
3. LIFF設定：
   - **LIFFアプリ名**: 従業員登録
   - **サイズ**: Full
   - **エンドポイントURL**: `https://your-domain.com/register` (ngrokなど使用)
   - **Scope**: profile, openid
   - **ボットリンク機能**: On (推奨)
4. LIFF IDを取得（例: `1234567890-abcdefgh`）

### 3. Webhookの設定

1. チャネルの「Messaging API」タブを開く
2. Webhook設定：
   - **Webhook URL**: `https://your-domain.com/webhook`
   - **Webhookの利用**: ON
3. QRコードから友だち追加できることを確認

## 🚀 セットアップ手順

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd 一斉送信
```

### 2. Python仮想環境の作成

```bash
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. 依存パッケージのインストール

```bash
pip install -r requirements.txt
```

### 4. 環境変数の設定

`.env.example` をコピーして `.env` ファイルを作成：

```bash
cp .env.example .env
```

`.env` ファイルを編集して、取得した情報を入力：

```env
LINE_CHANNEL_ACCESS_TOKEN=your_actual_channel_access_token
LINE_CHANNEL_SECRET=your_actual_channel_secret
LIFF_ID=your_actual_liff_id

SECRET_KEY=your_random_secret_key_for_flask
FLASK_ENV=development
```

### 5. データベース初期化

```bash
python database.py
```

これにより、データベースとサンプル勤務場所が作成されます。

### 6. アプリケーションの起動

```bash
python app.py
```

ローカルでは `http://127.0.0.1:5000` でアクセスできます。

### 7. 公開URL取得（ngrok使用）

開発環境でLIFFを使用する場合、ngrokなどで公開URLが必要です：

```bash
# 別のターミナルで実行
ngrok http 5000
```

取得したHTTPS URL（例: `https://abcd1234.ngrok.io`）を：
- LIFFのエンドポイントURL: `https://abcd1234.ngrok.io/register`
- Webhook URL: `https://abcd1234.ngrok.io/webhook`

として設定してください。

## 📖 使い方

### 管理者の操作

#### 1. 従業員の追加

1. ブラウザで `http://127.0.0.1:5000/employees` にアクセス
2. 「新規従業員追加」フォームに入力
   - **従業員名**: 山田太郎
   - **従業員番号**: EMP001
3. 「追加」ボタンをクリック

#### 2. 勤務連絡の送信

1. メイン画面 (`http://127.0.0.1:5000`) にアクセス
2. **共通設定**を入力（全員に共通の初期値）：
   - 勤務日: カレンダーから選択
   - 勤務場所: ドロップダウンから選択
   - 出勤時間: 時刻を入力
3. 「共通設定を全員に適用」ボタンをクリック（オプション）
4. 送信したい従業員のチェックボックスを選択
5. 必要に応じて個別に日時・場所を調整
6. 「選択した従業員に送信」ボタンをクリック

### 従業員の操作

#### LINE登録手順

1. LINE公式アカウントを友だち追加
2. 管理者から提供されたLIFF URL（`https://liff.line.me/your-liff-id`）を開く
3. LINEログインを許可
4. 従業員番号を入力（例: EMP001）
5. 「登録する」ボタンをクリック
6. 「登録完了！」と表示されたら完了

これで勤務連絡を受け取れるようになります。

## 📁 プロジェクト構造

```
一斉送信/
├── app.py                 # メインアプリケーション
├── database.py            # データベース管理
├── line_sender.py         # LINE送信機能
├── requirements.txt       # Python依存パッケージ
├── .env                   # 環境変数（作成必要）
├── .env.example           # 環境変数のテンプレート
├── .gitignore            # Git除外設定
├── database.db           # SQLiteデータベース（自動生成）
├── templates/            # HTMLテンプレート
│   ├── index.html        # メイン送信画面
│   ├── employees.html    # 従業員管理画面
│   └── register.html     # LIFF登録画面
└── static/               # 静的ファイル（CSS/JS）
```

## 🗄️ データベース構造

### employees（従業員テーブル）
- `id`: 主キー
- `name`: 従業員名
- `employee_number`: 従業員番号（ユニーク）
- `line_user_id`: LINEユーザーID
- `created_at`: 登録日時

### workplaces（勤務場所マスタ）
- `id`: 主キー
- `name`: 場所名
- `sort_order`: 表示順

### work_schedules（勤務予定・送信履歴）
- `id`: 主キー
- `employee_id`: 従業員ID（外部キー）
- `work_date`: 勤務日
- `workplace`: 勤務場所
- `work_time`: 出勤時間
- `sent_at`: 送信日時
- `created_at`: 作成日時

## 🔧 カスタマイズ

### 勤務場所の追加

`database.py` を編集して勤務場所を追加：

```python
add_workplace('新宿オフィス', 6)
add_workplace('横浜オフィス', 7)
```

または、データベースに直接追加：

```bash
sqlite3 database.db
INSERT INTO workplaces (name, sort_order) VALUES ('新宿オフィス', 6);
```

### メッセージフォーマットの変更

`line_sender.py` の `send_work_notification` 関数を編集：

```python
# 現在のフォーマット
message = f"{work_date} {workplace} {work_time} お願いします"

# カスタマイズ例
message = f"""
【勤務連絡】
日付: {work_date}
場所: {workplace}
時間: {work_time}
よろしくお願いいたします。
""".strip()
```

## ⚠️ トラブルシューティング

### 送信エラーが発生する

1. `.env` の `LINE_CHANNEL_ACCESS_TOKEN` が正しいか確認
2. LINE Developers ConsoleでMessaging APIが有効か確認
3. トークン有効期限が切れていないか確認

### 従業員登録ができない

1. LIFF IDが正しく設定されているか確認
2. LIFF URLが正しい公開URLになっているか確認
3. ブラウザのコンソールでエラーを確認

### データベースエラー

```bash
# データベースをリセット
rm database.db
python database.py
```

## 🔒 セキュリティ

- `.env` ファイルは **絶対にGitにコミットしない**
- 本番環境では `.gitignore` で除外されていることを確認
- 本番環境では `FLASK_ENV=production` に設定
- SECRET_KEYは必ずランダムな値に変更

## 📝 ライセンス

MIT License

## 🤝 サポート

問題が発生した場合は、Issue を作成してください。
