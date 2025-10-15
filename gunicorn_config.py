"""
Gunicorn設定ファイル - 本番環境用WSGIサーバー設定
"""
import multiprocessing
import os

# サーバーソケット設定
bind = f"0.0.0.0:{os.getenv('PORT', '5001')}"  # デプロイ先によってはPORT環境変数を使用
backlog = 2048

# ワーカープロセス設定
workers = multiprocessing.cpu_count() * 2 + 1  # 推奨値: CPUコア数 * 2 + 1
worker_class = "sync"  # 同期ワーカー（APSchedulerと互換性あり）
worker_connections = 1000
max_requests = 1000  # メモリリーク対策: 1000リクエストごとにワーカーを再起動
max_requests_jitter = 50  # ランダム性を追加して一斉再起動を防ぐ
timeout = 120  # タイムアウト（秒）- LINEからの応答待ち時間を考慮
keepalive = 5

# ログ設定
accesslog = "-"  # 標準出力にアクセスログを出力
errorlog = "-"   # 標準エラー出力にエラーログを出力
loglevel = "info"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# プロセス名
proc_name = "line_bot_app"

# デーモン化（本番環境では通常Falseのまま、systemdやsupervisorが管理）
daemon = False

# pidファイル
pidfile = None

# ユーザー/グループ（必要に応じて設定）
# user = "www-data"
# group = "www-data"

# 環境変数
raw_env = [
    # 本番環境フラグ
    "FLASK_ENV=production",
]

# セキュリティ設定
limit_request_line = 4094  # リクエスト行の最大サイズ
limit_request_fields = 100  # ヘッダーフィールドの最大数
limit_request_field_size = 8190  # ヘッダーフィールドの最大サイズ

# 起動時の処理
def on_starting(server):
    """サーバー起動時のフック"""
    print("🚀 Gunicornサーバーを起動中...")

def on_reload(server):
    """リロード時のフック"""
    print("🔄 Gunicornサーバーをリロード中...")

def when_ready(server):
    """サーバー準備完了時のフック"""
    print("✅ Gunicornサーバー起動完了")
    print(f"📍 ワーカー数: {workers}")
    print(f"📍 バインドアドレス: {bind}")

def on_exit(server):
    """サーバー終了時のフック"""
    print("🛑 Gunicornサーバーを終了中...")

def worker_exit(server, worker):
    """ワーカープロセス終了時のフック"""
    print(f"👷 ワーカー {worker.pid} が終了しました")
