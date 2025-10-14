# oder.rtf 実装計画

## 📋 プロジェクト概要
公式LINEから各アルバイトスタッフへ勤務時間の連絡を一斉送信できるアプリの機能拡張

**実装開始日**: 2025-10-14
**Git Branch**: feature/oder-requirements

---

## 🎯 6つの機能要件

### Feature #1: ウィザード送信履歴削減
- [ ] ウィザードの送信ボタンでは`work_schedules`テーブルに保存しない
- [ ] 送信セッションは残す（既存機能維持）
- [ ] 実装ファイル:
  - [ ] `app.py`: `/wizard/send` エンドポイント追加
  - [ ] `templates/wizard.html`: フォームaction変更
  - [ ] 警告バナー追加「この送信方法では履歴が残りません」

### Feature #2: 勤務場所管理
- [ ] アプリ上で勤務場所を追加・編集・削除
- [ ] `workplaces`テーブルに`is_active`カラム追加（デフォルト: 1）
- [ ] 実装ファイル:
  - [ ] `database.py`: CRUD関数追加
    - [ ] `add_workplace(name, sort_order)`
    - [ ] `update_workplace(id, name, sort_order, is_active)`
    - [ ] `delete_workplace(id)` → 論理削除
  - [ ] `app.py`: `/workplaces/*` エンドポイント群
  - [ ] `templates/settings.html`: 📍勤務場所管理セクション追加

### Feature #3: 時間入力UI改善
- [x] **設定画面の返信期限時刻**: 時(HH)と分(MM)を分離
- [ ] **送信ウィザードの勤務時間**: 時(HH)と分(MM)を分離
- [ ] 15分刻みの分セレクトボックス (00, 15, 30, 45)
- [ ] カスタム入力も可能に
- [ ] 実装ファイル:
  - [ ] `static/js/time-picker.js`: 時間選択UIコンポーネント（約100行）
  - [ ] `static/css/time-picker.css`: スタイリング（約150行）
  - [ ] `templates/wizard.html`: 勤務時間入力部分を置き換え
  - [ ] `templates/settings.html`: 返信期限時刻入力を置き換え（優先実装）

### Feature #4: 設定画面再構成
- [x] **セクション順序変更完了**: ⏰返信期限 → 👥通知先社員 → 🔒パスワード → 👔従業員種別
- [x] **モダンなカードベースデザイン適用済み**
- [x] ホバーエフェクト追加済み
- [x] `templates/settings.html`: 完全リファクタリング完了

### Feature #5: 従業員番号スマート採番
- [ ] 新規従業員追加時、従業員番号は手動入力ではなくプルダウン選択
- [ ] 使用済み番号は表示しない（例: k00000, k00001, k00003 → k00002, k00004以降を表示）
- [ ] 実装ファイル:
  - [ ] `database.py`: `get_available_employee_numbers()` 関数
  - [ ] `app.py`: `/api/available_employee_numbers` エンドポイント
  - [ ] `templates/employees.html`: 従業員番号入力をselect要素に変更
  - [ ] JavaScript: 動的に選択肢更新

### Feature #6: 従業員在籍管理
- [ ] `employees`テーブルに`is_active`カラム追加（デフォルト: 1）
- [ ] 「従業員在籍管理」セクション新設
- [ ] 在籍中/退職済みの切り替え、編集、削除機能
- [ ] 送信画面では在籍中の従業員のみ表示
- [ ] 実装ファイル:
  - [ ] `database.py`: マイグレーション + CRUD関数
    - [ ] `add_is_active_to_employees()` マイグレーション
    - [ ] `set_employee_inactive(id)`
    - [ ] `get_active_employees()`
  - [ ] `app.py`: `/employees/*` エンドポイント拡張
  - [ ] `templates/employees.html`: 在籍管理UI追加
  - [ ] `templates/wizard.html`: `get_active_employees()`を使用

---

## 📊 実装フェーズ

### ✅ PHASE 0: 環境準備とバックアップ (完了)
- [x] プロジェクト構造確認
- [x] `database.py`の`get_all_workplaces()`確認 → **既存テーブル発見！リスク低減**
- [x] `static/js/`, `static/css/` ディレクトリ作成
- [x] データベースバックアップ: `database.db.backup_20251014_185016`
- [x] Git初期化 + feature branch作成: `feature/oder-requirements`

### 🔄 PHASE 1: フロントエンド変更（スキーマ変更なし）
- [x] **Feature #4**: 設定画面再構成（完了！）
- [ ] **Feature #3**: 時間入力UI改善
  - [ ] time-picker.js/css作成
  - [ ] wizard.html修正
  - [ ] settings.html修正
- [ ] **Feature #1**: ウィザード送信履歴削減

### ⏳ PHASE 2: バックエンドロジック（スキーマ変更なし）
- [ ] **Feature #5**: 従業員番号スマート採番
- [ ] `/api/available_employee_numbers` エンドポイント

### ⚠️ PHASE 3: データベース変更 - employees（要バックアップ#2）
- [ ] **バックアップ#2作成**: `database.db.backup_[timestamp]`
- [ ] **Feature #6**: 従業員在籍管理
  - [ ] `ALTER TABLE employees ADD COLUMN is_active INTEGER DEFAULT 1`
  - [ ] 関連エンドポイント実装
  - [ ] UI実装

### ⚠️ PHASE 4: データベース変更 - workplaces（要バックアップ#3）
- [ ] **バックアップ#3作成**: `database.db.backup_[timestamp]`
- [ ] **Feature #2**: 勤務場所管理
  - [ ] `ALTER TABLE workplaces ADD COLUMN is_active INTEGER DEFAULT 1`
  - [ ] CRUD実装
  - [ ] UI実装

### 🎉 PHASE 5: テストと仕上げ
- [ ] 全機能の動作テスト
- [ ] モバイルレスポンシブ確認
- [ ] アクセシビリティ検証
- [ ] ドキュメント更新
- [ ] ユーザー受け入れテスト

---

## 🎨 UI/UXデザインシステム

### カラーパレット
- **Primary**: Indigo (#4F46E5) - ボタン、リンク
- **Success**: Emerald (#10B981) - 成功メッセージ
- **Warning**: Amber (#F59E0B) - 注意
- **Danger**: Red (#EF4444) - 削除、エラー
- **Neutral**: Slate (#64748B) - テキスト

### コンポーネント
- **Card**: `box-shadow: 0 2px 4px rgba(0,0,0,0.1)`, `border-radius: 8px`
- **Hover**: `box-shadow: 0 4px 8px rgba(0,0,0,0.15)`
- **アイコン**: 絵文字使用（⏰👥🔒👔📍⚙️）
- **Spacing**: `margin-bottom: 1.5rem`, `padding: 1.5rem`

### アクセシビリティ
- WCAG 2.1 Level AA準拠
- キーボードナビゲーション対応
- スクリーンリーダー対応
- 色覚異常対応（色だけに依存しない）

---

## 🔧 技術スタック

- **Backend**: Flask 3.0.0 + Python 3.9
- **Database**: SQLite3 (Row factory)
- **Frontend**: Bootstrap 5.3.0 + Vanilla JS
- **Scheduler**: APScheduler (13:00, 14:00 cron)
- **LINE**: line-bot-sdk 3.9.0 (deprecated but functional)

---

## 📝 注意事項

### 既存機能の保護
- **送信履歴機能**: Feature #1実装時も既存の送信フローは維持
- **スケジューラー**: 13:00, 14:00の自動チェックは変更なし
- **通知機能**: 社員への通知サマリーは維持

### データ安全性
- **段階的バックアップ**: 各PHASE開始前に必ずバックアップ
- **ロールバック手順**: `cp database.db.backup_[timestamp] database.db`
- **マイグレーション検証**: 本番適用前にバックアップDBで検証

### テスト項目
- [ ] 既存の送信フローが正常動作するか
- [ ] スケジューラーが正常動作するか
- [ ] 新機能が要件通り動作するか
- [ ] モバイル環境でも使いやすいか
- [ ] アクセシビリティが確保されているか

---

## 📅 進捗ログ

### 2025-10-14
- ✅ PHASE 0完了: 環境準備、Git初期化
- ✅ Feature #4完了: 設定画面再構成（モダンデザイン適用）
- 🔄 次: Feature #3（時間入力UI改善）またはブラウザ確認

---

## 🚀 次のアクション

1. **現在**: ブラウザで設定画面の変更を確認中
2. **次**: Feature #3（時間入力UI改善）の実装
3. **その後**: Feature #1（ウィザード送信履歴削減）の実装
