"""定数・設定"""
from pathlib import Path

BASE_DIR = Path(__file__).parent
DB_PATH = BASE_DIR / "data" / "jobs.db"
PROMPTS_DIR = BASE_DIR / "prompts"

# 候補者プロフィールのフィールド定義
CANDIDATE_FIELDS = {
    "name": {"label": "氏名", "type": "text"},
    "age": {"label": "年齢", "type": "number"},
    "current_company": {"label": "現在の会社", "type": "text"},
    "current_role": {"label": "現在の職種", "type": "text"},
    "experience_summary": {"label": "職務経歴概要", "type": "textarea"},
    "desired_job_type": {"label": "希望職種", "type": "text"},
    "desired_salary": {"label": "希望年収", "type": "text"},
    "desired_location": {"label": "希望勤務地", "type": "text"},
    "desired_overtime": {"label": "希望残業時間", "type": "text"},
    "desired_schedule": {"label": "希望勤務形態", "type": "text"},
    "timeline": {"label": "転職希望時期", "type": "text"},
    "transfer_reason": {"label": "転職理由", "type": "textarea"},
    "skills": {"label": "スキル・強み", "type": "textarea"},
    "special_circumstances": {"label": "特記事項", "type": "textarea"},
}

# 求人DBカラム定義
JOB_COLUMNS = [
    "company_name",   # 会社名
    "job_title",      # 求人タイトル
    "job_type",       # 職種
    "salary_min",     # 年収下限（万円）
    "salary_max",     # 年収上限（万円）
    "location",       # 勤務地
    "overtime_hours",  # 残業時間
    "work_schedule",  # 雇用形態
    "description",    # 仕事内容
    "requirements",   # 応募条件
    "benefits",       # 福利厚生
    "source_url",     # 求人元URL
    "source",         # 取得元（indeed/csv/manual）
]

# CSVインポート時の日本語ヘッダーマッピング
CSV_COLUMN_MAP = {
    "会社名": "company_name",
    "求人タイトル": "job_title",
    "職種": "job_type",
    "年収下限（万円）": "salary_min",
    "年収上限（万円）": "salary_max",
    "年収下限": "salary_min",
    "年収上限": "salary_max",
    "勤務地": "location",
    "残業時間": "overtime_hours",
    "雇用形態": "work_schedule",
    "仕事内容": "description",
    "応募条件": "requirements",
    "福利厚生": "benefits",
}

# 関連職種マッピング（マッチングスコア用）
RELATED_JOB_TYPES = {
    "事務": ["一般事務", "営業事務", "経理事務", "総務事務", "医療事務", "受付事務", "人事事務", "貿易事務"],
    "営業": ["法人営業", "個人営業", "ルート営業", "営業事務", "企画営業", "提案営業"],
    "エンジニア": ["SE", "プログラマー", "ITエンジニア", "Web開発", "インフラエンジニア"],
    "接客": ["販売", "ホテル", "飲食", "サービス", "カスタマーサポート"],
}

# マッチングスコアの重み
MATCHING_WEIGHTS = {
    "job_type": 30,
    "salary": 25,
    "location": 20,
    "overtime": 10,
    "work_schedule": 10,
    "skills_match": 5,
}
