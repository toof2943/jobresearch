"""ルールベースの求人マッチングスコアリング"""
import re
import pandas as pd
from config import MATCHING_WEIGHTS, RELATED_JOB_TYPES


def rank_jobs(candidate: dict, jobs_df: pd.DataFrame) -> pd.DataFrame:
    """全求人にスコアを付けてランキング"""
    if jobs_df.empty:
        return jobs_df

    scores = jobs_df.apply(lambda row: score_job(candidate, row), axis=1)
    scores_df = pd.DataFrame(scores.tolist())
    result = pd.concat([jobs_df.reset_index(drop=True), scores_df], axis=1)
    return result.sort_values("total_score", ascending=False).reset_index(drop=True)


def score_job(candidate: dict, job) -> dict:
    """候補者と求人のマッチスコアを計算"""
    scores = {}
    scores["score_job_type"] = _score_job_type(
        candidate.get("desired_job_type", ""),
        str(job.get("job_type", "") or "") + " " + str(job.get("job_title", "") or ""),
    )
    scores["score_salary"] = _score_salary(
        candidate.get("desired_salary", ""),
        job.get("salary_min"),
        job.get("salary_max"),
    )
    scores["score_location"] = _score_location(
        candidate.get("desired_location", ""),
        str(job.get("location", "") or ""),
    )
    scores["score_overtime"] = _score_overtime(
        candidate.get("desired_overtime", ""),
        str(job.get("overtime_hours", "") or ""),
    )
    scores["score_schedule"] = _score_schedule(
        candidate.get("desired_schedule", ""),
        str(job.get("work_schedule", "") or ""),
    )
    scores["score_skills"] = _score_skills(
        candidate.get("skills", ""),
        str(job.get("description", "") or "") + " " + str(job.get("requirements", "") or ""),
    )
    scores["total_score"] = sum(scores.values())
    return scores


def _score_job_type(desired: str, job_text: str) -> int:
    """職種マッチ（最大30点）"""
    max_score = MATCHING_WEIGHTS["job_type"]
    if not desired or not job_text:
        return 0

    desired = desired.strip()
    job_text = job_text.strip()

    # 完全一致（部分文字列含む）
    if desired in job_text:
        return max_score

    # 関連職種チェック
    for category, related in RELATED_JOB_TYPES.items():
        if desired in category or category in desired:
            for r in related:
                if r in job_text:
                    return int(max_score * 0.7)
        for r in related:
            if desired in r or r in desired:
                if any(r2 in job_text for r2 in related) or category in job_text:
                    return int(max_score * 0.5)

    return 0


def _score_salary(desired_text: str, job_min, job_max) -> int:
    """年収マッチ（最大25点）"""
    max_score = MATCHING_WEIGHTS["salary"]
    desired_val = _extract_salary(str(desired_text or ""))
    if desired_val is None:
        return int(max_score * 0.5)  # 条件不明→部分点

    jmin = _to_int(job_min)
    jmax = _to_int(job_max)

    if jmin is None and jmax is None:
        return int(max_score * 0.3)  # 給与不明

    # 希望年収がレンジ内
    if jmax and desired_val <= jmax:
        if jmin and desired_val >= jmin:
            return max_score  # ぴったりレンジ内
        return int(max_score * 0.8)

    # 近い範囲（±20%）
    if jmax:
        if desired_val <= jmax * 1.2:
            return int(max_score * 0.5)

    if jmin:
        if desired_val >= jmin * 0.8:
            return int(max_score * 0.6)

    return 0


def _score_location(desired: str, job_location: str) -> int:
    """勤務地マッチ（最大20点）"""
    max_score = MATCHING_WEIGHTS["location"]
    if not desired or not job_location:
        return 0

    desired_tokens = _split_location(desired)
    job_tokens = _split_location(job_location)

    for dt in desired_tokens:
        for jt in job_tokens:
            if dt in jt or jt in dt:
                return max_score

    # 同じ都道府県レベル
    prefectures = [
        "東京", "神奈川", "大阪", "愛知", "埼玉", "千葉", "福岡", "北海道",
        "京都", "兵庫", "静岡", "広島", "茨城", "宮城", "新潟",
    ]
    for pref in prefectures:
        if pref in desired and pref in job_location:
            return int(max_score * 0.8)

    # 首都圏マッチ
    tokyo_area = ["東京", "神奈川", "埼玉", "千葉", "横浜", "川崎"]
    desired_in_tokyo = any(t in desired for t in tokyo_area)
    job_in_tokyo = any(t in job_location for t in tokyo_area)
    if desired_in_tokyo and job_in_tokyo:
        return int(max_score * 0.6)

    return 0


def _score_overtime(desired: str, job_overtime: str) -> int:
    """残業マッチ（最大10点）"""
    max_score = MATCHING_WEIGHTS["overtime"]
    desired_hours = _extract_hours(str(desired or ""))
    job_hours = _extract_hours(str(job_overtime or ""))

    if desired_hours is None:
        return int(max_score * 0.5)
    if job_hours is None:
        return int(max_score * 0.3)

    if job_hours <= desired_hours:
        return max_score
    if job_hours <= desired_hours * 1.5:
        return int(max_score * 0.5)
    return 0


def _score_schedule(desired: str, job_schedule: str) -> int:
    """雇用形態マッチ（最大10点）"""
    max_score = MATCHING_WEIGHTS["work_schedule"]
    if not desired or not job_schedule:
        return int(max_score * 0.5)

    if desired in job_schedule or job_schedule in desired:
        return max_score
    return 0


def _score_skills(skills_text: str, job_text: str) -> int:
    """スキルマッチ（最大5点）"""
    max_score = MATCHING_WEIGHTS["skills_match"]
    if not skills_text or not job_text:
        return 0

    # スキルをトークン化
    skills = re.split(r"[,、\n・\-]", skills_text)
    skills = [s.strip() for s in skills if len(s.strip()) >= 2]

    if not skills:
        return 0

    matches = sum(1 for s in skills if s in job_text)
    ratio = matches / len(skills) if skills else 0
    return int(max_score * min(ratio * 2, 1.0))


# --- ヘルパー ---

def _extract_salary(text: str):
    if not text:
        return None
    m = re.search(r"(\d[\d,]*)\s*万", text)
    if m:
        return int(m.group(1).replace(",", ""))
    m = re.search(r"(\d+)", text)
    if m and int(m.group(1)) > 100:
        return int(m.group(1))
    return None


def _to_int(val):
    if val is None:
        return None
    try:
        v = int(float(val))
        return v if v > 0 else None
    except (ValueError, TypeError):
        return None


def _split_location(text: str) -> list[str]:
    tokens = re.split(r"[,、/／\s　]+", text)
    return [t.strip() for t in tokens if t.strip()]


def _extract_hours(text: str):
    if not text:
        return None
    m = re.search(r"(\d+)\s*[時h]", text)
    if m:
        return int(m.group(1))
    m = re.search(r"(\d+)", text)
    if m:
        return int(m.group(1))
    if "なし" in text or "ゼロ" in text or "0" in text:
        return 0
    return None
