from typing import Optional, List, Dict, Tuple
from app.repositories.employee_repository import EmployeeRepository
import logging

logger = logging.getLogger(__name__)

class EmployeeService:
    """従業員ビジネスロジック"""

    def __init__(self):
        self.repo = EmployeeRepository()

    def get_employee_by_number(self, employee_number: str) -> Optional[Dict]:
        """従業員番号から従業員を取得"""
        try:
            return self.repo.find_by_employee_number(employee_number)
        except Exception as e:
            logger.error(f"Failed to get employee {employee_number}: {e}")
            raise

    def get_employee_by_line_id(self, line_user_id: str) -> Optional[Dict]:
        """LINE IDから従業員を取得"""
        try:
            return self.repo.find_by_line_user_id(line_user_id)
        except Exception as e:
            logger.error(f"Failed to get employee by LINE ID: {e}")
            raise

    def register_line_user(
        self,
        employee_number: str,
        line_user_id: str,
        employee_name: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """LINE登録処理

        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            # 従業員の存在確認
            employee = self.repo.find_by_employee_number(employee_number)
            if not employee:
                return (False, "従業員番号が見つかりません")

            # 名前確認（指定された場合）
            if employee_name and employee['name'] != employee_name:
                return (False, "従業員名が一致しません")

            # 既に別のLINEアカウントに紐付いている場合
            if employee['line_user_id'] and employee['line_user_id'] != line_user_id:
                return (False, "この従業員番号は既に別のLINEアカウントに登録されています")

            # LINE ID更新
            self.repo.update_line_id(employee_number, line_user_id, employee_name)
            logger.info(f"LINE registration successful: {employee_number}")
            return (True, None)

        except Exception as e:
            logger.error(f"LINE registration failed: {e}")
            return (False, f"登録処理でエラーが発生しました: {str(e)}")

    def list_all_employees(self) -> List[Dict]:
        """全従業員リストを取得"""
        try:
            return self.repo.find_all_active()
        except Exception as e:
            logger.error(f"Failed to list employees: {e}")
            raise

    def create_employee(
        self,
        employee_number: str,
        name: str
    ) -> Tuple[bool, Optional[str]]:
        """新規従業員作成

        Returns:
            (success: bool, error_message: Optional[str])
        """
        try:
            # 重複チェック
            existing = self.repo.find_by_employee_number(employee_number)
            if existing:
                return (False, "この従業員番号は既に存在します")

            employee_id = self.repo.create(employee_number, name)
            logger.info(f"Employee created: {employee_number} (ID: {employee_id})")
            return (True, None)

        except Exception as e:
            logger.error(f"Failed to create employee: {e}")
            return (False, f"作成処理でエラーが発生しました: {str(e)}")

    def soft_delete_employee(self, employee_id: int) -> Tuple[bool, Optional[str]]:
        """従業員を論理削除"""
        try:
            self.repo.soft_delete(employee_id)
            logger.info(f"Employee soft deleted: {employee_id}")
            return (True, None)
        except Exception as e:
            logger.error(f"Failed to soft delete employee: {e}")
            return (False, str(e))

    def hard_delete_employee(self, employee_id: int) -> Tuple[bool, Optional[str]]:
        """従業員を物理削除（番号再利用のため）"""
        try:
            self.repo.hard_delete(employee_id)
            logger.info(f"Employee hard deleted: {employee_id}")
            return (True, None)
        except Exception as e:
            logger.error(f"Failed to hard delete employee: {e}")
            return (False, str(e))
