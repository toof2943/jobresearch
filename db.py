"""SQLiteデータベース操作"""
import sqlite3
import pandas as pd
from config import DB_PATH, CSV_COLUMN_MAP, JOB_COLUMNS

ALLOWED_COLUMNS = set(JOB_COLUMNS + ["source_url", "source"])


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(str(DB_PATH))


def init_db():
    with _get_conn() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_name TEXT,
                job_title TEXT,
                job_type TEXT,
                salary_min INTEGER,
                salary_max INTEGER,
                location TEXT,
                overtime_hours TEXT,
                work_schedule TEXT,
                description TEXT,
                requirements TEXT,
                benefits TEXT,
                source_url TEXT,
                source TEXT DEFAULT 'manual',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def _sanitize_job(job: dict) -> dict:
    return {k: v for k, v in job.items() if k in ALLOWED_COLUMNS}


def get_all_jobs() -> pd.DataFrame:
    with _get_conn() as conn:
        df = pd.read_sql_query("SELECT * FROM jobs ORDER BY created_at DESC", conn)
    return df


def add_job(job: dict) -> int:
    sanitized = _sanitize_job(job)
    cols = [k for k in sanitized if k not in ("id", "created_at")]
    if not cols:
        return 0
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    values = [sanitized[k] for k in cols]
    with _get_conn() as conn:
        cursor = conn.execute(
            f"INSERT INTO jobs ({col_names}) VALUES ({placeholders})", values
        )
        return cursor.lastrowid


def add_jobs_bulk(jobs: list[dict]) -> int:
    if not jobs:
        return 0
    sanitized_jobs = [_sanitize_job(j) for j in jobs]
    cols = [k for k in sanitized_jobs[0] if k not in ("id", "created_at")]
    if not cols:
        return 0
    placeholders = ", ".join(["?"] * len(cols))
    col_names = ", ".join(cols)
    rows = [[j.get(k) for k in cols] for j in sanitized_jobs]
    with _get_conn() as conn:
        conn.executemany(
            f"INSERT INTO jobs ({col_names}) VALUES ({placeholders})", rows
        )
        return len(rows)


def update_job(job_id: int, job: dict):
    sanitized = _sanitize_job(job)
    cols = [k for k in sanitized if k not in ("id", "created_at")]
    if not cols:
        return
    set_clause = ", ".join([f"{c} = ?" for c in cols])
    values = [sanitized[k] for k in cols] + [job_id]
    with _get_conn() as conn:
        conn.execute(f"UPDATE jobs SET {set_clause} WHERE id = ?", values)


def delete_job(job_id: int):
    with _get_conn() as conn:
        conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))


def import_csv(df: pd.DataFrame) -> int:
    # 日本語ヘッダーをマッピング
    rename_map = {}
    for col in df.columns:
        col_stripped = col.strip()
        if col_stripped in CSV_COLUMN_MAP:
            rename_map[col] = CSV_COLUMN_MAP[col_stripped]
        else:
            rename_map[col] = col_stripped
    df = df.rename(columns=rename_map)

    # 有効なカラムだけ残す
    valid_cols = [
        "company_name", "job_title", "job_type", "salary_min", "salary_max",
        "location", "overtime_hours", "work_schedule", "description",
        "requirements", "benefits", "source_url",
    ]
    existing = [c for c in valid_cols if c in df.columns]
    if not existing:
        return 0
    df = df[existing].copy()
    df["source"] = "csv"

    # 数値変換
    for col in ["salary_min", "salary_max"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    records = df.to_dict("records")
    return add_jobs_bulk(records)


def search_jobs(filters: dict) -> pd.DataFrame:
    """フィルタ条件で求人を検索"""
    query = "SELECT * FROM jobs WHERE 1=1"
    params = []

    if filters.get("job_type"):
        query += " AND (job_type LIKE ? OR job_title LIKE ?)"
        params.extend([f"%{filters['job_type']}%"] * 2)

    if filters.get("location"):
        query += " AND location LIKE ?"
        params.append(f"%{filters['location']}%")

    if filters.get("salary_min"):
        query += " AND (salary_max >= ? OR salary_max IS NULL)"
        params.append(filters["salary_min"])

    query += " ORDER BY created_at DESC"

    with _get_conn() as conn:
        return pd.read_sql_query(query, conn, params=params)
