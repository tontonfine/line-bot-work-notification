from typing import Dict, List, Optional
from database import get_db_connection
import logging

logger = logging.getLogger(__name__)

class BaseRepository:
    """ベースリポジトリクラス"""

    def _get_connection(self):
        """データベース接続を取得"""
        return get_db_connection()

    def _execute_query(self, query: str, params: tuple = ()) -> Optional[Dict]:
        """単一行を返すクエリを実行"""
        conn = self._get_connection()
        try:
            result = conn.execute(query, params).fetchone()
            return dict(result) if result else None
        except Exception as e:
            logger.error(f"Query failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()

    def _execute_query_all(self, query: str, params: tuple = ()) -> List[Dict]:
        """複数行を返すクエリを実行"""
        conn = self._get_connection()
        try:
            results = conn.execute(query, params).fetchall()
            return [dict(row) for row in results]
        except Exception as e:
            logger.error(f"Query failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()

    def _execute_write(self, query: str, params: tuple = ()) -> int:
        """書き込みクエリを実行（INSERT/UPDATE/DELETE）"""
        conn = self._get_connection()
        try:
            conn.execute('BEGIN IMMEDIATE')
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.lastrowid
        except Exception as e:
            conn.rollback()
            logger.error(f"Write failed: {query[:50]}... - {e}")
            raise
        finally:
            conn.close()
