"""
Supabase 기반 데이터베이스 관리자
기존 execute_query 인터페이스를 유지하면서 Supabase REST API로 변환
"""

import re
import json
import threading
from contextlib import contextmanager
from typing import Optional, Any, List, Tuple, Dict

# 마지막 INSERT ID 추적
_last_insert_id = 0
_connection_lock = threading.Lock()


class SupabaseRow(dict):
    """sqlite3.Row와 호환되는 딕셔너리 래퍼. dict 접근 및 인덱스 접근 모두 지원."""

    def __init__(self, data: dict, columns: list = None):
        super().__init__(data)
        self._columns = columns or list(data.keys())

    def __getitem__(self, key):
        if isinstance(key, int):
            col = self._columns[key]
            return super().__getitem__(col)
        return super().__getitem__(key)

    def keys(self):
        return self._columns


def _get_client():
    """Supabase 클라이언트를 가져옵니다."""
    from database.supabase_client import get_supabase_client
    return get_supabase_client()


def get_db_connection():
    """호환성 유지용. Supabase 클라이언트를 반환합니다."""
    return _get_client()


def close_connection():
    """호환성 유지용. Supabase는 연결 관리 불필요."""
    pass


@contextmanager
def db_transaction():
    """호환성 유지용. Supabase는 트랜잭션을 REST API로 직접 지원하지 않음."""
    yield _get_client()


def _parse_sql(query: str, params: Optional[Tuple] = None) -> dict:
    """
    간단한 SQL을 파싱하여 Supabase API 호출 정보로 변환합니다.
    지원 패턴: SELECT, INSERT, UPDATE, DELETE, INSERT OR REPLACE
    """
    query = query.strip()
    # 파라미터 치환: ? → 실제 값
    param_list = list(params) if params else []

    result = {
        'operation': None,
        'table': None,
        'columns': '*',
        'values': {},
        'conditions': [],
        'order_by': None,
        'order_dir': 'asc',
        'limit': None,
        'is_count': False,
        'is_upsert': False,
        'set_values': {},
    }

    # 정규화
    q = ' '.join(query.split())

    # SELECT COUNT(*)
    count_match = re.match(
        r'SELECT\s+COUNT\(\*\)\s+(?:as\s+\w+\s+)?FROM\s+(\w+)',
        q, re.IGNORECASE
    )
    if count_match:
        result['operation'] = 'SELECT'
        result['table'] = count_match.group(1)
        result['is_count'] = True
        # WHERE 절 파싱
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|\s*$)', q, re.IGNORECASE)
        if where_match:
            result['conditions'] = _parse_where(where_match.group(1), param_list)
        return result

    # SELECT
    select_match = re.match(
        r'SELECT\s+(.+?)\s+FROM\s+(\w+)(.*)',
        q, re.IGNORECASE
    )
    if select_match:
        result['operation'] = 'SELECT'
        result['columns'] = select_match.group(1).strip()
        result['table'] = select_match.group(2)
        rest = select_match.group(3).strip()

        # WHERE
        where_match = re.search(r'WHERE\s+(.+?)(?:\s+ORDER|\s+LIMIT|\s*$)', rest, re.IGNORECASE)
        if where_match:
            result['conditions'] = _parse_where(where_match.group(1), param_list)

        # ORDER BY
        order_match = re.search(r'ORDER\s+BY\s+(\w+)(?:\s+(ASC|DESC))?', rest, re.IGNORECASE)
        if order_match:
            result['order_by'] = order_match.group(1)
            if order_match.group(2):
                result['order_dir'] = order_match.group(2).lower()

        # LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', rest, re.IGNORECASE)
        if limit_match:
            result['limit'] = int(limit_match.group(1))

        return result

    # INSERT OR REPLACE / INSERT OR IGNORE
    upsert_match = re.match(
        r'INSERT\s+OR\s+(?:REPLACE|IGNORE)\s+INTO\s+(\w+)\s*\((.+?)\)\s*VALUES\s*\((.+?)\)',
        q, re.IGNORECASE
    )
    if upsert_match:
        result['operation'] = 'UPSERT'
        result['table'] = upsert_match.group(1)
        columns = [c.strip() for c in upsert_match.group(2).split(',')]
        result['values'] = _build_values(columns, param_list)
        result['is_upsert'] = True
        return result

    # INSERT
    insert_match = re.match(
        r'INSERT\s+INTO\s+(\w+)\s*\((.+?)\)\s*VALUES\s*\((.+?)\)',
        q, re.IGNORECASE
    )
    if insert_match:
        result['operation'] = 'INSERT'
        result['table'] = insert_match.group(1)
        columns = [c.strip() for c in insert_match.group(2).split(',')]
        result['values'] = _build_values(columns, param_list)
        return result

    # UPDATE
    update_match = re.match(
        r'UPDATE\s+(\w+)\s+SET\s+(.+?)(?:\s+WHERE\s+(.+?))?$',
        q, re.IGNORECASE
    )
    if update_match:
        result['operation'] = 'UPDATE'
        result['table'] = update_match.group(1)
        set_clause = update_match.group(2).strip()
        result['set_values'] = _parse_set(set_clause, param_list)
        if update_match.group(3):
            result['conditions'] = _parse_where(update_match.group(3), param_list)
        return result

    # DELETE
    delete_match = re.match(
        r'DELETE\s+FROM\s+(\w+)(?:\s+WHERE\s+(.+?))?$',
        q, re.IGNORECASE
    )
    if delete_match:
        result['operation'] = 'DELETE'
        result['table'] = delete_match.group(1)
        if delete_match.group(2):
            result['conditions'] = _parse_where(delete_match.group(2), param_list)
        return result

    raise ValueError(f"지원하지 않는 SQL 패턴: {query}")


def _parse_where(where_str: str, params: list) -> list:
    """WHERE 절을 조건 리스트로 파싱합니다."""
    conditions = []
    # AND로 분리
    parts = re.split(r'\s+AND\s+', where_str, flags=re.IGNORECASE)
    for part in parts:
        part = part.strip()
        # col = ?
        eq_match = re.match(r'(\w+)\s*=\s*\?', part)
        if eq_match:
            val = params.pop(0) if params else None
            conditions.append(('eq', eq_match.group(1), val))
            continue
        # col != ?
        neq_match = re.match(r'(\w+)\s*!=\s*\?', part)
        if neq_match:
            val = params.pop(0) if params else None
            conditions.append(('neq', neq_match.group(1), val))
            continue
        # col > ?
        gt_match = re.match(r'(\w+)\s*>\s*\?', part)
        if gt_match:
            val = params.pop(0) if params else None
            conditions.append(('gt', gt_match.group(1), val))
            continue
        # col >= ?
        gte_match = re.match(r'(\w+)\s*>=\s*\?', part)
        if gte_match:
            val = params.pop(0) if params else None
            conditions.append(('gte', gte_match.group(1), val))
            continue
        # col LIKE ?
        like_match = re.match(r'(\w+)\s+LIKE\s+\?', part, re.IGNORECASE)
        if like_match:
            val = params.pop(0) if params else None
            conditions.append(('like', like_match.group(1), val))
            continue
        # col IN (?, ?, ...)
        in_match = re.match(r'(\w+)\s+IN\s*\((.+?)\)', part, re.IGNORECASE)
        if in_match:
            placeholders = in_match.group(2).split(',')
            vals = [params.pop(0) for _ in placeholders if params]
            conditions.append(('in', in_match.group(1), vals))
            continue
        # col = 'literal'
        eq_lit_match = re.match(r"(\w+)\s*=\s*'([^']*)'", part)
        if eq_lit_match:
            conditions.append(('eq', eq_lit_match.group(1), eq_lit_match.group(2)))
            continue
        # col != 'literal'
        neq_lit_match = re.match(r"(\w+)\s*!=\s*'([^']*)'", part)
        if neq_lit_match:
            conditions.append(('neq', neq_lit_match.group(1), neq_lit_match.group(2)))
            continue

    return conditions


def _parse_set(set_str: str, params: list) -> dict:
    """SET 절을 딕셔너리로 파싱합니다."""
    values = {}
    parts = set_str.split(',')
    for part in parts:
        part = part.strip()
        match = re.match(r'(\w+)\s*=\s*\?', part)
        if match:
            col = match.group(1)
            val = params.pop(0) if params else None
            if col in _JSONB_COLUMNS:
                val = _try_parse_json(val)
            values[col] = val
        else:
            # col = 'literal' 또는 col = CURRENT_TIMESTAMP
            lit_match = re.match(r"(\w+)\s*=\s*'([^']*)'", part)
            if lit_match:
                values[lit_match.group(1)] = lit_match.group(2)
            else:
                func_match = re.match(r"(\w+)\s*=\s*(\S+)", part)
                if func_match:
                    values[func_match.group(1)] = func_match.group(2)
    return values


def _try_parse_json(val):
    """문자열이 JSON 객체/배열이면 파싱하여 dict/list로 반환합니다. (JSONB 컬럼 호환)"""
    if isinstance(val, str) and val.strip() and val.strip()[0] in ('{', '['):
        try:
            return json.loads(val)
        except (json.JSONDecodeError, ValueError):
            pass
    return val


# JSONB 컬럼 목록 (Supabase에서 JSONB 타입인 컬럼)
_JSONB_COLUMNS = {
    'session_data', 'progress_data', 'settings_data', 'block_data', 'shared_with_teams'
}


def _build_values(columns: list, params: list) -> dict:
    """컬럼 목록과 파라미터를 딕셔너리로 변환합니다."""
    values = {}
    for col in columns:
        val = params.pop(0) if params else None
        # JSONB 컬럼이면 문자열을 dict/list로 변환
        if col in _JSONB_COLUMNS:
            val = _try_parse_json(val)
        values[col] = val
    return values


def _apply_conditions(query_builder, conditions: list):
    """Supabase 쿼리빌더에 조건을 적용합니다."""
    for op, col, val in conditions:
        if op == 'eq':
            query_builder = query_builder.eq(col, val)
        elif op == 'neq':
            query_builder = query_builder.neq(col, val)
        elif op == 'gt':
            query_builder = query_builder.gt(col, val)
        elif op == 'gte':
            query_builder = query_builder.gte(col, val)
        elif op == 'like':
            # SQLite LIKE → Supabase ilike
            query_builder = query_builder.ilike(col, val)
        elif op == 'in':
            query_builder = query_builder.in_(col, val)
    return query_builder


def execute_query(
    query: str,
    params: Optional[Tuple] = None,
    commit: bool = False
) -> List[SupabaseRow]:
    """
    SQL 쿼리를 파싱하여 Supabase REST API로 실행합니다.
    기존 SQLite execute_query와 동일한 인터페이스를 유지합니다.
    """
    global _last_insert_id

    with _connection_lock:
        try:
            parsed = _parse_sql(query, params)
        except ValueError as e:
            print(f"⚠️ SQL 파싱 실패: {e}")
            return []

        client = _get_client()
        table = parsed['table']

        try:
            if parsed['operation'] == 'SELECT':
                if parsed['is_count']:
                    qb = client.table(table).select('*', count='exact')
                    qb = _apply_conditions(qb, parsed['conditions'])
                    result = qb.limit(1).execute()
                    count_val = result.count if result.count is not None else 0
                    # COUNT 결과를 SupabaseRow로 반환 (다양한 alias 호환)
                    row_data = {'count': count_val, 'cnt': count_val, 'COUNT(*)': count_val}
                    return [SupabaseRow(row_data, ['count'])]

                select_cols = parsed['columns']
                qb = client.table(table).select(select_cols)
                qb = _apply_conditions(qb, parsed['conditions'])

                if parsed['order_by']:
                    desc = parsed['order_dir'] == 'desc'
                    qb = qb.order(parsed['order_by'], desc=desc)

                if parsed['limit']:
                    qb = qb.limit(parsed['limit'])

                result = qb.execute()
                return [SupabaseRow(row) for row in (result.data or [])]

            elif parsed['operation'] == 'INSERT':
                # None 값인 키는 제거 (DB 기본값 사용)
                values = {k: v for k, v in parsed['values'].items() if v is not None}
                result = client.table(table).insert(values).execute()
                if result.data:
                    _last_insert_id = result.data[0].get('id', 0)
                return [SupabaseRow(row) for row in (result.data or [])]

            elif parsed['operation'] == 'UPSERT':
                values = parsed['values']
                # on_conflict 컬럼 추정: unique 제약 조건 기반
                conflict_cols = _get_conflict_column(table)
                result = client.table(table).upsert(
                    values, on_conflict=conflict_cols
                ).execute()
                if result.data:
                    _last_insert_id = result.data[0].get('id', 0)
                return [SupabaseRow(row) for row in (result.data or [])]

            elif parsed['operation'] == 'UPDATE':
                qb = client.table(table).update(parsed['set_values'])
                qb = _apply_conditions(qb, parsed['conditions'])
                result = qb.execute()
                return [SupabaseRow(row) for row in (result.data or [])]

            elif parsed['operation'] == 'DELETE':
                qb = client.table(table).delete()
                qb = _apply_conditions(qb, parsed['conditions'])
                result = qb.execute()
                return [SupabaseRow(row) for row in (result.data or [])]

        except Exception as e:
            print(f"⚠️ Supabase 쿼리 오류 [{parsed['operation']} {table}]: {e}")
            raise e

    return []


def _get_conflict_column(table: str) -> str:
    """테이블별 UPSERT 충돌 컬럼을 반환합니다."""
    conflict_map = {
        'api_keys': 'user_id,key_name',
        'user_settings': 'user_id',
        'analysis_progress': 'user_id',
        'users': 'personal_number',
    }
    return conflict_map.get(table, 'id')


def execute_many(
    query: str,
    params_list: List[Tuple],
    commit: bool = True
) -> int:
    """여러 개의 쿼리를 배치로 실행합니다."""
    count = 0
    for params in params_list:
        execute_query(query, params, commit=commit)
        count += 1
    return count


def get_last_insert_id() -> int:
    """마지막으로 삽입된 행의 ID를 반환합니다."""
    return _last_insert_id


def table_exists(table_name: str) -> bool:
    """Supabase에 테이블이 존재하는지 확인합니다."""
    try:
        client = _get_client()
        client.table(table_name).select('id').limit(1).execute()
        return True
    except Exception:
        return False
