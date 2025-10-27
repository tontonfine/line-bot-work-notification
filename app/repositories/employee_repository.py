from typing import List, Optional, Dict
from .base_repository import BaseRepository
import logging

logger = logging.getLogger(__name__)

class EmployeeRepository(BaseRepository):
    """従業員データアクセスリポジトリ"""

    def find_by_id(self, employee_id: int) -> Optional[Dict]:
        """IDから従業員を取得"""
        return self._execute_query(
            'SELECT * FROM employees WHERE id = ?',
            (employee_id,)
        )

    def find_by_employee_number(self, employee_number: str) -> Optional[Dict]:
        """従業員番号から従業員を取得（大文字小文字区別なし）"""
        return self._execute_query(
            'SELECT * FROM employees WHERE LOWER(employee_number) = LOWER(?)',
            (employee_number,)
        )

    def find_all_active(self) -> List[Dict]:
        """有効な従業員全員を取得"""
        return self._execute_query_all(
            'SELECT * FROM employees WHERE is_deleted = 0 ORDER BY employee_number'
        )

    def find_by_line_user_id(self, line_user_id: str) -> Optional[Dict]:
        """LINE IDから従業員を取得"""
        return self._execute_query(
            'SELECT * FROM employees WHERE line_user_id = ?',
            (line_user_id,)
        )

    def update_line_id(
        self,
        employee_number: str,
        line_user_id: str,
        employee_name: Optional[str] = None
    ) -> None:
        """LINE IDを更新"""
        if employee_name:
            self._execute_write(
                '''UPDATE employees
                   SET line_user_id = ?, name = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE LOWER(employee_number) = LOWER(?)''',
                (line_user_id, employee_name, employee_number)
            )
        else:
            self._execute_write(
                '''UPDATE employees
                   SET line_user_id = ?, updated_at = CURRENT_TIMESTAMP
                   WHERE LOWER(employee_number) = LOWER(?)''',
                (line_user_id, employee_number)
            )
        logger.info(f"Updated LINE ID for employee: {employee_number}")

    def create(
        self,
        employee_number: str,
        name: str,
        line_user_id: Optional[str] = None
    ) -> int:
        """新規従業員作成"""
        employee_id = self._execute_write(
            'INSERT INTO employees (employee_number, name, line_user_id) VALUES (?, ?, ?)',
            (employee_number, name, line_user_id)
        )
        logger.info(f"Created employee: {employee_number} (ID: {employee_id})")
        return employee_id

    def soft_delete(self, employee_id: int) -> None:
        """論理削除"""
        self._execute_write(
            'UPDATE employees SET is_deleted = 1 WHERE id = ?',
            (employee_id,)
        )
        logger.info(f"Soft deleted employee: {employee_id}")

    def hard_delete(self, employee_id: int) -> None:
        """物理削除（番号再利用のため）"""
        self._execute_write(
            'DELETE FROM employees WHERE id = ?',
            (employee_id,)
        )
        logger.info(f"Hard deleted employee: {employee_id}")
