import os
import gspread
from google.oauth2.service_account import Credentials
from database import add_employee, update_employee_active_status, get_all_employees
from dotenv import load_dotenv

load_dotenv()

# Google Sheets認証情報のパス
CREDENTIALS_FILE = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def get_sheets_client():
    """
    Google Sheets APIクライアントを取得

    Returns:
        gspread.Client: 認証済みのクライアント
    """
    # 認証スコープ
    scopes = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]

    # サービスアカウント認証
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scopes)
    client = gspread.authorize(creds)

    return client

def fetch_employees_from_sheet():
    """
    Googleスプレッドシートから従業員データを取得

    データ構造:
    - A列: タイムスタンプ
    - B列: ユーザーID（従業員番号）
    - C列: メアド
    - D列: 姓 名
    - E列: 雇用形態（1=アルバイト, 2=社員）
    - F列: 管理権限
    - G列: 退職フラグ（空白=在職中, 1=退職）

    Returns:
        list: 従業員データのリスト
            [
                {
                    'employee_number': 'k00000',
                    'name': '近藤 魁斗',
                    'employee_type': 'part_time' or 'full_time',
                    'is_active': True or False
                },
                ...
            ]
    """
    if not SPREADSHEET_ID:
        raise ValueError("SPREADSHEET_ID が .env ファイルに設定されていません")

    try:
        client = get_sheets_client()
        spreadsheet = client.open_by_key(SPREADSHEET_ID)

        # 「従業員マスタ」シートを取得（シート名で指定）
        try:
            worksheet = spreadsheet.worksheet('従業員マスタ')
        except:
            # シート名が違う場合は最初のシートを使用
            print("⚠️ '従業員マスタ'シートが見つかりません。最初のシートを使用します。")
            worksheet = spreadsheet.get_worksheet(0)

        # 全データを取得（ヘッダー含む）
        all_values = worksheet.get_all_values()

        print(f"📊 取得した行数: {len(all_values)}")
        if len(all_values) > 0:
            print(f"📋 ヘッダー: {all_values[0]}")
        if len(all_values) > 1:
            print(f"📝 サンプルデータ（1行目）: {all_values[1][:7]}")  # 最初の7列のみ表示

        if len(all_values) < 2:
            return []

        # ヘッダー行をスキップして処理
        employees = []
        for row in all_values[1:]:  # 1行目はヘッダー
            # 最低限必要な列数をチェック（B, D, E列があればOK）
            if len(row) < 5:
                continue

            # B列: ユーザーID（従業員番号）
            employee_number = row[1].strip() if len(row) > 1 else ''
            if not employee_number:
                continue

            # D列: 姓 名
            name = row[3].strip() if len(row) > 3 else ''
            if not name:
                continue

            # E列: 雇用形態（1=アルバイト, 2=社員）
            employment_type_value = row[4].strip() if len(row) > 4 else ''
            if employment_type_value == '1':
                employee_type = 'part_time'
            elif employment_type_value == '2':
                employee_type = 'full_time'
            else:
                # デフォルトはアルバイト
                employee_type = 'part_time'

            # G列: 退職フラグ（空白=在職中, 1=退職）
            # G列が存在しない場合は全員在職中とみなす
            retirement_flag = row[6].strip() if len(row) > 6 else ''
            is_active = (retirement_flag != '1')

            employees.append({
                'employee_number': employee_number,
                'name': name,
                'employee_type': employee_type,
                'is_active': is_active
            })

        return employees

    except Exception as e:
        import traceback
        print(f"❌ スプレッドシートからのデータ取得エラー: {e}")
        print(f"詳細: {traceback.format_exc()}")
        raise

def sync_employees_from_sheet():
    """
    Googleスプレッドシートから従業員データを同期

    処理内容:
    1. スプレッドシートから全従業員データを取得
    2. 既存のDBデータと比較
    3. 新規従業員を追加
    4. 既存従業員の情報を更新（在籍状況、雇用形態）

    Returns:
        dict: 同期結果
            {
                'success': True/False,
                'added': 追加件数,
                'updated': 更新件数,
                'total': 合計処理件数,
                'errors': エラーメッセージリスト
            }
    """
    try:
        # スプレッドシートからデータ取得
        sheet_employees = fetch_employees_from_sheet()

        if not sheet_employees:
            return {
                'success': False,
                'error': 'スプレッドシートにデータがありません',
                'added': 0,
                'updated': 0,
                'total': 0
            }

        # 既存の従業員データを取得
        db_employees = get_all_employees()
        db_employee_numbers = {emp['employee_number']: emp for emp in db_employees}

        added_count = 0
        updated_count = 0
        errors = []

        for sheet_emp in sheet_employees:
            employee_number = sheet_emp['employee_number']

            # DBに存在するか確認
            if employee_number in db_employee_numbers:
                # 既存従業員の更新
                db_emp = db_employee_numbers[employee_number]

                # 在籍状況が変更されている場合
                if db_emp['is_active'] != sheet_emp['is_active']:
                    try:
                        update_employee_active_status(
                            db_emp['id'],
                            1 if sheet_emp['is_active'] else 0
                        )
                        updated_count += 1
                    except Exception as e:
                        errors.append(f"{employee_number}: ステータス更新失敗 - {e}")

                # TODO: 雇用形態の更新も必要な場合は追加

            else:
                # 新規従業員の追加
                try:
                    add_employee(
                        name=sheet_emp['name'],
                        employee_number=employee_number,
                        employee_type=sheet_emp['employee_type']
                    )

                    # 退職フラグが立っている場合は即座に退職処理
                    if not sheet_emp['is_active']:
                        # 追加直後なので、employee_numberで再取得
                        new_db_employees = get_all_employees()
                        for emp in new_db_employees:
                            if emp['employee_number'] == employee_number:
                                update_employee_active_status(emp['id'], 0)
                                break

                    added_count += 1
                except Exception as e:
                    errors.append(f"{employee_number}: 追加失敗 - {e}")

        return {
            'success': True,
            'added': added_count,
            'updated': updated_count,
            'total': len(sheet_employees),
            'errors': errors
        }

    except Exception as e:
        return {
            'success': False,
            'error': str(e),
            'added': 0,
            'updated': 0,
            'total': 0
        }

if __name__ == '__main__':
    # テスト実行
    print("🔄 スプレッドシート同期テスト")
    result = sync_employees_from_sheet()

    if result['success']:
        print(f"✅ 同期成功")
        print(f"   新規追加: {result['added']}件")
        print(f"   更新: {result['updated']}件")
        print(f"   合計: {result['total']}件")
        if result.get('errors'):
            print(f"   エラー: {len(result['errors'])}件")
            for error in result['errors']:
                print(f"     - {error}")
    else:
        print(f"❌ 同期失敗: {result.get('error', '不明なエラー')}")
