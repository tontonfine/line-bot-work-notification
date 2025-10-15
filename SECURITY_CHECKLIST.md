# セキュリティチェックリスト 🔐

デプロイ前に必ず確認してください。

## ✅ デプロイ前必須チェック

### 環境変数とシークレット

- [ ] `SECRET_KEY`が32文字以上のランダムな文字列である
- [ ] `SECRET_KEY`が`.env`ファイルに保存され、Gitにコミットされていない
- [ ] `LINE_CHANNEL_SECRET`が正しく設定されている
- [ ] `LINE_CHANNEL_ACCESS_TOKEN`が正しく設定されている
- [ ] `.env`ファイルが`.gitignore`に含まれている

### Flask設定

- [ ] `FLASK_ENV=production`に設定されている
- [ ] `FLASK_DEBUG=False`に設定されている（本番環境）
- [ ] `SESSION_COOKIE_SECURE=True`が有効（HTTPS環境）
- [ ] `SESSION_COOKIE_HTTPONLY=True`が有効
- [ ] `SESSION_COOKIE_SAMESITE='Lax'`が設定されている

### セキュリティ機能

- [ ] bcryptによるパスワードハッシュ化が実装されている
- [ ] CSRF保護（Flask-WTF）が有効
- [ ] レート制限（Flask-Limiter）が設定されている
- [ ] セキュリティヘッダー（Flask-Talisman）が本番環境で有効
- [ ] 入力検証が主要エンドポイントに実装されている

### 認証情報

- [ ] 初期管理者パスワードが12文字以上の複雑なもの
- [ ] 初期パスワードを安全な場所に保存した
- [ ] パスワードポリシーが強制されている（大文字、小文字、数字）
- [ ] Google API認証情報（credentials.json）がGitにコミットされていない

### データベース

- [ ] データベースファイル（*.db）が`.gitignore`に含まれている
- [ ] SQLインジェクション対策（パラメータ化クエリ）が実装されている
- [ ] データベースバックアップの仕組みがある

### ログとモニタリング

- [ ] セキュリティログ（security.log）が有効
- [ ] 失敗したログイン試行がログに記録される
- [ ] 不正な入力がログに記録される
- [ ] ログファイルが`.gitignore`に含まれている

### ネットワークセキュリティ

- [ ] HTTPSが有効（デプロイ先で自動的に有効化）
- [ ] 不要なポートが開いていない
- [ ] ファイアウォールが適切に設定されている（VPSの場合）

### コード品質

- [ ] XSS対策が実装されている（危険な文字のエスケープ）
- [ ] HTMLインジェクション対策が実装されている
- [ ] ファイルアップロード機能のバリデーション（該当する場合）
- [ ] エラーメッセージにスタックトレースが含まれない（本番環境）

### 依存関係

- [ ] `requirements.txt`が最新
- [ ] 既知の脆弱性がある依存関係がない
- [ ] 不要な依存関係が含まれていない

### その他

- [ ] Webhook URLが正しく設定されている
- [ ] LIFF Endpoint URLが正しく設定されている
- [ ] スケジューラーが正常に動作する
- [ ] タイムゾーンがAsia/Tokyoに設定されている

---

## 🔒 本番環境推奨設定

### app.py 確認事項

```python
# ✅ これが設定されていることを確認
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY must be set!")

app.config['SESSION_COOKIE_SECURE'] = True  # HTTPSのみ
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# ✅ 本番環境でTalismanが有効
IS_PRODUCTION = os.getenv('FLASK_ENV') == 'production'
if IS_PRODUCTION:
    Talisman(app, ...)

# ✅ デバッグモードが環境変数で制御
DEBUG_MODE = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'
```

### .env 確認事項

```bash
# ✅ 本番環境設定
FLASK_ENV=production
FLASK_DEBUG=False

# ✅ 強力なSECRET_KEY（32文字以上）
SECRET_KEY=<64文字のランダムな16進数文字列>

# ✅ LINE認証情報
LINE_CHANNEL_ACCESS_TOKEN=<正しいトークン>
LINE_CHANNEL_SECRET=<正しいシークレット>
LIFF_ID=<正しいLIFF ID>
```

### gunicorn_config.py 確認事項

```python
# ✅ 本番環境設定
bind = "0.0.0.0:5001"
workers = 1  # APScheduler使用時は1推奨
timeout = 120
loglevel = "info"
```

---

## 🛡️ デプロイ後のセキュリティ確認

### 1. HTTPS接続確認

```bash
# ブラウザでアクセスして鍵マークを確認
https://your-domain.com
```

### 2. セキュリティヘッダー確認

```bash
curl -I https://your-domain.com
```

以下のヘッダーが含まれていることを確認:
- `Strict-Transport-Security`
- `X-Frame-Options`
- `X-Content-Type-Options`
- `X-XSS-Protection`

### 3. CSRF保護確認

1. ブラウザのデベロッパーツールを開く
2. Networkタブで POST リクエストを確認
3. `X-CSRFToken`ヘッダーが含まれていることを確認

### 4. レート制限確認

同じエンドポイントに連続してリクエストを送り、制限がかかることを確認

### 5. ログ確認

```bash
# Renderの場合
Dashboard > Logs

# VPSの場合
sudo tail -f /var/www/line-bot/security.log
```

失敗したログイン試行などが記録されていることを確認

---

## 🚨 緊急時の対応

### パスワード漏洩の疑い

1. 即座に管理画面からパスワードを変更
2. `security.log`で不正アクセスを確認
3. 必要に応じてアプリケーションを一時停止

### 不正アクセス検出

1. アプリケーションを一時停止
2. ログを確認して攻撃パターンを特定
3. IPアドレスをブロック（該当する場合）
4. パスワードとSECRET_KEYを変更
5. 全ユーザーに通知

### データ漏洩の疑い

1. 即座にアプリケーションを停止
2. ログを保存して分析
3. 影響範囲を特定
4. 関係者に通知
5. 必要に応じて LINE に報告

---

## 📊 定期セキュリティレビュー（推奨: 月次）

- [ ] 依存関係の脆弱性スキャン
```bash
pip install safety
safety check
```

- [ ] パスワードの定期変更（3ヶ月ごと）
- [ ] ログレビュー（異常なアクセスパターン）
- [ ] データベースバックアップの確認
- [ ] HTTPS証明書の有効期限確認
- [ ] 不要なログファイルの削除

---

## ✅ チェックリスト完了確認

すべての項目にチェックが入ったら、デプロイ準備完了です！

**署名**: ___________________
**日付**: ___________________

---

**最終更新**: 2025年10月15日
**バージョン**: 1.0.0
