#!/bin/bash

echo "🚀 LINE勤務連絡システム セットアップスクリプト"
echo "================================================"
echo ""

# Python のバージョン確認
echo "📌 Pythonバージョン確認..."
python3 --version

if [ $? -ne 0 ]; then
    echo "❌ Python 3 がインストールされていません"
    exit 1
fi

# 仮想環境の作成
echo ""
echo "📦 仮想環境を作成中..."
python3 -m venv venv

if [ $? -ne 0 ]; then
    echo "❌ 仮想環境の作成に失敗しました"
    exit 1
fi

# 仮想環境を有効化
echo "✅ 仮想環境を有効化中..."
source venv/bin/activate

# パッケージのインストール
echo ""
echo "📥 依存パッケージをインストール中..."
pip install --upgrade pip
pip install -r requirements.txt

if [ $? -ne 0 ]; then
    echo "❌ パッケージのインストールに失敗しました"
    exit 1
fi

# .env ファイルの作成確認
echo ""
if [ ! -f .env ]; then
    echo "📝 .env ファイルを作成中..."
    cp .env.example .env
    echo "⚠️  .env ファイルを編集して、LINE APIの情報を設定してください"
    echo "   必要な情報: LINE_CHANNEL_ACCESS_TOKEN, LINE_CHANNEL_SECRET, LIFF_ID"
else
    echo "✅ .env ファイルは既に存在します"
fi

# データベース初期化
echo ""
echo "🗄️  データベースを初期化中..."
python database.py

if [ $? -ne 0 ]; then
    echo "❌ データベースの初期化に失敗しました"
    exit 1
fi

echo ""
echo "✅ セットアップ完了！"
echo ""
echo "📋 次のステップ:"
echo "   1. .env ファイルを編集して LINE API の情報を設定"
echo "   2. python app.py でアプリを起動"
echo "   3. http://127.0.0.1:5000 にアクセス"
echo ""
echo "🔧 開発環境での公開URL取得（LIFF使用時）:"
echo "   ngrok http 5000"
echo ""
