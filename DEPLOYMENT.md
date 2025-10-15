# デプロイメントガイド 🚀

このドキュメントは、LINE Bot勤務連絡システムを本番環境にデプロイする手順を説明します。

## 📋 目次

1. [デプロイ前の準備](#デプロイ前の準備)
2. [セキュリティチェックリスト](#セキュリティチェックリスト)
3. [Renderへのデプロイ](#renderへのデプロイ-推奨)
4. [Railwayへのデプロイ](#railwayへのデプロイ)
5. [VPSへのデプロイ](#vpsへのデプロイ)
6. [デプロイ後の確認](#デプロイ後の確認)
7. [トラブルシューティング](#トラブルシューティング)

---

## デプロイ前の準備

### 1. 環境変数の準備

`.env.example`をコピーして`.env`を作成し、以下の値を設定してください:

```bash
# SECRET_KEYの生成
python -c 'import secrets; print(secrets.token_hex(32))'
```

**必須の環境変数:**

| 変数名 | 説明 | 取得方法 |
|--------|------|----------|
| `LINE_CHANNEL_ACCESS_TOKEN` | LINEチャネルアクセストークン | [LINE Developers Console](https://developers.line.biz/console/) |
| `LINE_CHANNEL_SECRET` | LINEチャネルシークレット | LINE Developers Console |
| `LIFF_ID` | LIFF ID | LINE Developers Console > LIFF設定 |
| `SECRET_KEY` | Flaskのセッション暗号化キー | 上記コマンドで生成 |
| `FLASK_ENV` | 環境（本番は`production`） | `production` |
| `FLASK_DEBUG` | デバッグモード（本番は`False`） | `False` |

**オプション:**
- `SPREADSHEET_ID`: Google Sheets連携を使用する場合
- `PORT`: ポート番号（デフォルト: 5001）

### 2. 依存関係の確認

```bash
pip install -r requirements.txt
```

### 3. データベースの初期化確認

アプリケーション起動時に自動的にデータベースが初期化されます。
初回起動時に表示される**初期パスワード**を必ず保存してください。

---

## セキュリティチェックリスト

デプロイ前に以下を確認してください:

- [ ] `SECRET_KEY`が32文字以上のランダムな文字列である
- [ ] `FLASK_ENV=production`に設定されている
- [ ] `FLASK_DEBUG=False`に設定されている
- [ ] `.env`ファイルがGitにコミットされていない（`.gitignore`で除外）
- [ ] `credentials.json`がGitにコミットされていない
- [ ] 初期管理者パスワードを安全な場所に保存した
- [ ] HTTPSが有効になっている（デプロイ先で自動的に有効化）
- [ ] データベースファイル（*.db）がGitにコミットされていない

---

## Renderへのデプロイ（推奨）

Renderは無料枠があり、簡単にデプロイできるため推奨です。

### ステップ 1: Renderアカウント作成

1. [Render](https://render.com/)にアクセス
2. GitHubアカウントで登録

### ステップ 2: 新しいWeb Serviceを作成

1. Dashboard > "New +" > "Web Service"をクリック
2. GitHubリポジトリを接続
3. 以下の設定を入力:

| 項目 | 値 |
|------|-----|
| **Name** | `line-bot-work-notification`（任意） |
| **Environment** | `Python 3` |
| **Region** | `Singapore`（最も近いリージョン） |
| **Branch** | `main`または`master` |
| **Build Command** | `pip install -r requirements.txt` |
| **Start Command** | `gunicorn -c gunicorn_config.py app:app` |
| **Instance Type** | `Free`（または`Starter`） |

### ステップ 3: 環境変数を設定

"Environment"タブで以下を追加:

```
LINE_CHANNEL_ACCESS_TOKEN=<your_token>
LINE_CHANNEL_SECRET=<your_secret>
LIFF_ID=<your_liff_id>
SECRET_KEY=<generated_secret_key>
FLASK_ENV=production
FLASK_DEBUG=False
```

### ステップ 4: デプロイ

"Create Web Service"をクリックすると自動的にデプロイが開始されます。

### ステップ 5: LINE Webhook設定

1. デプロイ完了後、RenderのURLをコピー（例: `https://your-app.onrender.com`）
2. LINE Developers Consoleに戻る
3. Webhook URL: `https://your-app.onrender.com/webhook`
4. "Webhookの利用"を有効化
5. "検証"ボタンで接続をテスト

---

## Railwayへのデプロイ

Railwayも簡単にデプロイできるプラットフォームです。

### ステップ 1: Railwayアカウント作成

1. [Railway](https://railway.app/)にアクセス
2. GitHubアカウントで登録

### ステップ 2: プロジェクト作成

1. "New Project" > "Deploy from GitHub repo"
2. リポジトリを選択

### ステップ 3: 環境変数設定

"Variables"タブで環境変数を追加（Renderと同じ）

### ステップ 4: 起動コマンド設定

1. "Settings"タブ
2. "Start Command": `gunicorn -c gunicorn_config.py app:app`
3. "Deploy"をクリック

### ステップ 5: ドメイン設定

1. "Settings" > "Domains"
2. "Generate Domain"をクリック
3. 生成されたURLをLINE Webhookに設定

---

## VPSへのデプロイ

Ubuntu 22.04 LTSを使用した手順です。

### ステップ 1: サーバーセットアップ

```bash
# システム更新
sudo apt update && sudo apt upgrade -y

# Python 3.11インストール
sudo apt install python3.11 python3.11-venv python3-pip -y

# Nginxインストール
sudo apt install nginx -y

# SSL証明書（Let's Encrypt）
sudo apt install certbot python3-certbot-nginx -y
```

### ステップ 2: アプリケーションデプロイ

```bash
# アプリケーションディレクトリ作成
sudo mkdir -p /var/www/line-bot
cd /var/www/line-bot

# Gitクローン
sudo git clone https://github.com/your-username/your-repo.git .

# 仮想環境作成
sudo python3.11 -m venv venv
source venv/bin/activate

# 依存関係インストール
pip install -r requirements.txt
```

### ステップ 3: 環境変数設定

```bash
sudo nano .env
```

必要な環境変数を入力して保存

### ステップ 4: Systemdサービス作成

```bash
sudo nano /etc/systemd/system/line-bot.service
```

以下の内容を貼り付け:

```ini
[Unit]
Description=LINE Bot Work Notification System
After=network.target

[Service]
Type=notify
User=www-data
Group=www-data
WorkingDirectory=/var/www/line-bot
Environment="PATH=/var/www/line-bot/venv/bin"
ExecStart=/var/www/line-bot/venv/bin/gunicorn -c gunicorn_config.py app:app
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

サービスを有効化:

```bash
sudo systemctl daemon-reload
sudo systemctl enable line-bot
sudo systemctl start line-bot
sudo systemctl status line-bot
```

### ステップ 5: Nginx設定

```bash
sudo nano /etc/nginx/sites-available/line-bot
```

以下の内容を貼り付け:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # タイムアウト設定
        proxy_connect_timeout 120s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }

    # 静的ファイル
    location /static {
        alias /var/www/line-bot/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    # セキュリティヘッダー
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;
}
```

設定を有効化:

```bash
sudo ln -s /etc/nginx/sites-available/line-bot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### ステップ 6: SSL証明書設定

```bash
sudo certbot --nginx -d your-domain.com
```

自動更新の確認:

```bash
sudo certbot renew --dry-run
```

---

## デプロイ後の確認

### 1. アプリケーション起動確認

デプロイ先のURLにアクセスして、メイン画面が表示されることを確認

### 2. LINE Webhook接続確認

LINE Developers Consoleで"検証"ボタンをクリックし、成功することを確認

### 3. LIFF動作確認

1. LIFFアプリのEndpoint URLを設定: `https://your-domain.com/register`
2. LINEアプリからLIFFを開いて動作確認

### 4. 初期パスワード確認

デプロイログを確認し、初期管理者パスワードを保存

**Renderの場合:**
- Dashboard > Logs > 初回起動ログを確認

**Railwayの場合:**
- "Deployments" > 最新デプロイ > "View Logs"

**VPSの場合:**
```bash
sudo journalctl -u line-bot -n 100
```

### 5. 管理画面ログイン

1. `https://your-domain.com/login`にアクセス
2. 初期パスワードでログイン
3. すぐにパスワードを変更（Settings > パスワード変更）

### 6. スケジューラー動作確認

ログで以下が表示されていることを確認:

```
✅ スケジューラーセットアップ完了
✅ 13:00チェックジョブ登録: 毎日13:00
✅ 14:00チェックジョブ登録: 毎日14:00
```

---

## トラブルシューティング

### デプロイが失敗する

**問題**: ビルドエラー

**解決策**:
1. `requirements.txt`に必要な依存関係がすべて含まれているか確認
2. Python バージョンが3.9以上か確認
3. ログを確認してエラーメッセージを特定

### アプリケーションが起動しない

**問題**: 起動時エラー

**解決策**:
1. 環境変数がすべて設定されているか確認（特に`SECRET_KEY`）
2. ログで具体的なエラーメッセージを確認
3. データベースの初期化エラーがないか確認

### LINE Webhookが接続できない

**問題**: Webhook検証失敗

**解決策**:
1. Webhook URLが正しいか確認（HTTPSである必要あり）
2. `LINE_CHANNEL_SECRET`が正しいか確認
3. アプリケーションが起動しているか確認
4. ファイアウォール設定を確認（VPSの場合）

### スケジューラーが動作しない

**問題**: 定期タスクが実行されない

**解決策**:
1. ログで「スケジューラーセットアップ完了」が表示されているか確認
2. タイムゾーンが正しく設定されているか確認（Asia/Tokyo）
3. ワーカープロセス数を確認（複数ワーカーの場合、スケジューラーが重複実行される可能性）

**推奨**: ワーカー数を1に設定（`gunicorn_config.py`で`workers = 1`）

### セッションが維持されない

**問題**: ログイン後すぐにログアウトされる

**解決策**:
1. `SECRET_KEY`が設定されているか確認
2. HTTPSが有効になっているか確認
3. `SESSION_COOKIE_SECURE`の設定を確認（本番環境ではTrue）

### メモリ不足エラー

**問題**: アプリケーションがクラッシュ

**解決策**:
1. ワーカー数を減らす（`gunicorn_config.py`で調整）
2. メモリ使用量を監視
3. より大きなインスタンスタイプにアップグレード

---

## セキュリティのベストプラクティス

### 定期的な更新

```bash
# 依存関係の更新確認
pip list --outdated

# セキュリティアップデート
pip install --upgrade <package-name>
```

### ログ監視

- `security.log`を定期的に確認
- 不正なログイン試行を監視
- 異常なアクセスパターンを検出

### バックアップ

定期的にデータベースをバックアップ:

```bash
# データベースバックアップ（1日1回推奨）
cp database.db database.db.backup_$(date +%Y%m%d)
```

### 環境変数の管理

- `.env`ファイルを安全に管理
- パスワードを定期的に変更
- 不要なアクセス権限を削除

---

## サポート

問題が解決しない場合:

1. [GitHub Issues](https://github.com/your-username/your-repo/issues)で報告
2. ログファイル（`security.log`, `app.log`）を添付
3. エラーメッセージの全文を含める
4. 環境情報（デプロイ先、Pythonバージョンなど）を記載

---

**最終更新**: 2025年10月15日
**バージョン**: 1.0.0
